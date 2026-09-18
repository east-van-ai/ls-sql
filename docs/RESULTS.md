# ls-sql at a million files

One tree, 1,048,576 files, every tag living in the filename. What it costs to
build, and what it costs to query.

## The corpus

| Parameter | Value |
| ----------- | ------- |
| **Files generated** | 2^20 (1,048,576) |
| **Total size** | ~4.3GB |
| **Generation time** | 120 seconds |
| **Throughput** | ~8,700 files/sec |
| **Per-file metadata** | ~4.5KB average |
| **Hardware** | M1 Air, 8GB RAM |
| **Date** | 2026-08-25 |

That 4.5KB row is measured, not guessed. Write 10,000 real files, read `df`
before and after, divide. It comes to 4,537 bytes each.

`du` on the same directory says 4,096, because `du` counts only the blocks
holding data. The 441 bytes between the two numbers is what the filesystem
spends remembering the file exists: its name, its dates, its permissions, and
where its block sits.

The 4,096 is APFS handing out space in whole blocks. A 30-byte file takes the
same room as a 4,000-byte one. So the sentences inside these files are free,
and the total is only ever the file count times 4,537.

## The questions

Three things to settle:

1. Whether the filename encoding survives a million files intact.
2. What a query costs against a raw filename-scan baseline.
3. How both numbers change on a spinning disk, and how they compare to SQLite.

## Method

### Generation

The corpus is generated from its own index. Five word pools of sixteen give
16^5 = 1,048,576 sentences, exactly the hex range `00000` to `FFFFF`. Each digit
picks one word, so every name and every byte is a pure function of the number.
Re-running a range reproduces the same bytes.

```bash
python tools/hatfile_generator.py data/hats 00000 FFFFF --commit
```

The words go into the name as `evai:` tags, so the tree is born harvested and
needs no harvest pass before querying.

```text
Bear-00000^^^evai:subject=bear^evai:verb=asked^evai:recipient=alligator^evai:colour=amber^evai:fruit=apple^^^.txt
```

The tree shards two levels, `<Subject>/<verb>/`, giving 256 leaf directories of
4,096 files each.

### Query baseline

Tags live in filenames, so the baseline is a filename scan, not a content scan.

```bash
# parallel baseline
time rg --files data/hats -g "*evai:fruit=apple*"

# single-threaded baseline
time find data/hats -name "*evai:fruit=apple*"

# ls-sql comparison
time ls-sql list data/hats -R --query "SELECT * WHERE evai:fruit='apple'"

# integrity
time ls-sql verify data/hats -R
```

ripgrep needs no flag to descend a gitignored path when that path is named
explicitly on the command line, so `data/hats` is walked without `--no-ignore`.

## Results

Three runs each, warm cache, M1 Air. Every tool returned the same 65,536
matches for `evai:fruit=apple`.

| Operation | Time | CPU | Notes |
| --- | --- | --- | --- |
| Generate 1M files | 120 sec | | Python CLI, no parallelism |
| `rg --files -g` | 1.03 sec | 247% | Parallel directory walker |
| `ls-sql list --query` | 13.8 sec | 52% | Single thread, stalls on I/O |
| `find -name` | 17.6 sec | 36% | Single thread, extra stat per entry |
| `ls-sql verify` | 11.3 sec | 53% | Walk cost, nothing checked |

`verify` checked nothing here, so its number is the bare walk cost. That is the
useful part: 11.3 of ls-sql's 13.8 seconds is reaching the filenames. Parsing
tags and printing 65,536 rows is the remaining 2.5.

ls-sql beats `find` by about 22%, doing strictly more work per entry. `find`
spends 4.23 sec in system time against ls-sql's 2.27, so `os.scandir` avoiding
a stat per entry more than pays for the tag parsing on top.

ripgrep is thirteen times faster than either, and uses less total CPU while
doing it. Both effects are real: a parallel walker, and a cheaper per-entry
cost.

## On a spinning disk

The same queries against an external HDD, full corpus, 65,536 matches each.

| Operation | Time | CPU | Files/sec |
| --- | --- | --- | --- |
| `rg --files -g` | 5m 26s | 2% | ~3,200 |
| `ls-sql list --query` | 6m 08s | 3% | ~2,850 |
| `find -name` | 13m 02s | 2% | ~1,340 |

`find` is the only clear result. At 2.4 times slower than the others it sits
far outside the run-to-run noise, and two runs agreed to within 5%.

ls-sql and ripgrep are tied. An earlier pair of runs had ls-sql ahead by 15%,
this pair has ripgrep ahead by 11%, and ls-sql's own per-file cost moved 24%
between its two runs. Anything claimed about which of those two is faster on a
platter would be reading a mechanism into noise.

The HDD sample is the thin one here. Two runs per tool, warm, and no cold run
at all, against three warm runs each on flash. An external USB SSD is the one
drive class still unmeasured, so the middle of the range is an estimate rather
than a number.

The number that does survive is what the change of storage costs each tool:

| | SSD | HDD | Ratio |
| --- | --- | --- | --- |
| `rg --files -g` | 1.0 sec | 5m 26s | 317x |
| `ls-sql list --query` | 13.1 sec | 6m 08s | 28x |
| `find -name` | 17.6 sec | 13m 02s | 43x |

ripgrep pays 317 times for moving to a platter. It was thirteen times faster
than ls-sql on flash and is level with it here. Its advantage was never really
the tool, it was the drive: many threads keep a solid-state queue full, and a
single head cannot be kept full at all. Every tool sits at 2 to 3 percent CPU
on the HDD, so none of them is computing anything. They are all just waiting.

## SQLite, for comparison

The same corpus loaded into SQLite, one row per file, one column per tag.
Measured with `tools/sqlite_bench.py` against the real tree rather than
synthesised rows.

| Operation | Time |
| --- | --- |
| Indexed lookup, 65,536 rows returned | 0.065 sec |
| Unindexed table scan, same result | 0.121 sec |
| `COUNT(*)` only | 0.001 sec |
| Load 1,048,576 rows from the tree | 13.74 sec |
| Create the index | 0.41 sec |
| Database on disk | 191.4 MB |

The unindexed scan is the fair comparison against ripgrep, since neither has an
index and both are scanning. SQLite is still eight times faster, because it
reads one compact table straight through while ripgrep walks a million separate
directory entries. A flat table is faster to scan than a tree is to walk.

There is no performance argument against a database. The argument is that the
191 MB file is wrong the moment anything is renamed outside the tool, and that
it can be rebuilt from the filenames in fourteen seconds whenever it is wanted.
That makes an index a cache you regenerate rather than a database you maintain.

## Findings

### What held

- Filename encoding survived generation intact
- No path-length collisions or truncation
- `list` parsed all 1M entries correctly
- `evai:` round-trips through the query parser

### The surprises

- ripgrep walks the same tree in 1 second. 82% of ls-sql's query time is the
  directory walk, not the parsing, and ripgrep shows the floor is about 1
  second rather than 11.
- ls-sql is faster than `find` at the identical task, despite parsing every
  filename into a tag dict. Avoiding a stat per entry is worth more than the
  parsing costs.
- ripgrep's advantage belongs to the drive, not to the tool. Thirteen times
  faster than ls-sql on flash, level with it on a platter. Moving to the HDD
  costs ripgrep a factor of 317, against ls-sql's 28. Whichever scanner is
  right depends on the storage, which is an argument for a format any of them
  can read.

## Conclusion

For reading, ls-sql is not the fast path on flash. ripgrep filters the same
corpus thirteen times faster there, and the two are level on a spinning disk.
What ls-sql has that a search tool does not:

- **Persistence**: metadata rides inside the name, so it survives copy and move
- **Harvesting**: no search tool can put the tags there in the first place
- **Reach**: any glob-capable tool reads the result, with no client to install

The million file test proves the filename encoding survives scale. The query
benchmarks say the read path is where the time goes, and that scanning is
better delegated than reimplemented.

Built on an M1 Air with 8GB RAM. No cloud, no PhD, just files and grep.

---

**East Van AI** · AI for the rest of us! · Vancouver, BC, Canada

[github.com/east-van-ai](https://github.com/east-van-ai) · <east-van-ai@proton.me>

MIT License · Copyright (c) 2026 Go Nakamaru
