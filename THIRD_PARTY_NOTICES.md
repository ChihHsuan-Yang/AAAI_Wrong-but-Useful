# Third-Party Notices

## Software dependencies

This artifact depends on the following open-source packages, each distributed
under its own license. Installing them via `requirements.lock` retrieves the
canonical upstream distributions and their license texts.

| Package | License |
|---|---|
| matplotlib | Matplotlib License (BSD-style, PSF-based) |
| numpy | BSD 3-Clause |
| PyYAML | MIT |
| pytest | MIT |
| zstandard | BSD 3-Clause |

The runtime code in `src/dhd/` is original to this artifact and is released
under the MIT License in `LICENSE`. The protocol runtime uses only the Python
standard library at run time.

## Benchmark datasets

This artifact does **not** redistribute any benchmark question text. The derived
aggregate statistics reference the following datasets, which must be obtained
from their upstream sources under their own licenses. Cite them under those
terms:

| Benchmark | License | Attribution requirement |
|---|---|---|
| Omni-MATH-2 | Upstream math-competition source terms | Cite upstream release |
| JEEBench | MIT | Cite upstream release |
| SciBench | MIT | Cite upstream release |
| LAB-Bench | CC-BY-SA-4.0 | Attribution + share-alike; preserve canary string |
| MaScQA | CC-BY-NC-SA-4.0 | Attribution + non-commercial + share-alike |

See `DATA.md` for the redistribution decision applied to each dataset.

## JEEBench (MIT) — reproduced content notice

`data/derived/integrator_uptake_audit.csv` reproduces a small number of short
JEEBench answer labels (e.g. `ACD`, numeric values) alongside author-written
reasoning paraphrases. JEEBench is distributed under the MIT License, which
permits redistribution provided its copyright and permission notice accompany the
copied material. The MIT permission text below is reproduced for that purpose;
replace the bracketed copyright line with the upstream JEEBench copyright holders
when citing the dataset's official release.

```
MIT License

Copyright (c) [year] [JEEBench dataset authors]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
