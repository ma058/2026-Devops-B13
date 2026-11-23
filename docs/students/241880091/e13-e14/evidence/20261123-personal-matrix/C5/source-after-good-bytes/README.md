# B13 bounded level monitor

Provider: B13 member2 241880091. Derived layout: B13 labs/e8e10/lab.py classroom mixed Make fixture at public import dd35a439f8fb67f5e4d8267cff54239a6ceaac54. The level-normalization CLI, input checking and executable self-tests are member2 additions. The missing dependencies are deliberately introduced classroom defects, not upstream bugs.

C0: normalize negative readings to zero, accept a decimal argument, reject invalid/range errors with exit 2. C1: introduce a configurable upper cap in extra.h and tests; deliberately omit main.o/config.h and helper.o/extra.h dependencies. The obsolete unused.h declaration remains as a REDUNDANT finding; repairs must keep HEADERS and $(HEADERS).

Build: make clean && make app. Test: make check. Run: ./app => 1 plus LF, exit 0. ./app 12: C0 prints 13, C1 prints 11. ./app invalid exits 2. ./app --self-test prints SELF_TEST=PASS plus LF, exit 0.

Supported: Linux/GCC, two root C translation units, explicit Make object rules, no symlinks/nested includes/dynamic Make expressions. Input/output is intentionally deterministic. No external real-project provenance is claimed. Original classroom-source attribution retained; added code is provided for this course exchange under MIT (see LICENSE).
