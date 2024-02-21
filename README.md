Rbugs: R bug dataset
================
Rbugs is a collection of 172 reproducible bugs.

Contents
================

Projects
---------------
Rbugs contains 172 bugs from 3 open-source projects:
| Project name | Number of bugs |
|--------------|----------------|
| dplyr        | 66             |
| ggplot2      | 87             |
| tibble       | 19             |

Bugs
---------------
Information for a specific bug is in `bug_list`.
The (b)uggy and (f)ixed program revisions are labelled with `<id>b` and `<id>f`, respectively (`<id>` is an integer).

Setting
================

Requirements
----------------
- R
- Python3
- [psutil](https://github.com/giampaolo/psutil/blob/master/INSTALL.rst)
- [GitPython](https://gitpython.readthedocs.io/en/stable/intro.html)
- libpq-dev

#### R version
See `bug_list` for recommended R version.

Recommended requirements
----------------
- Ubuntu20.04

Steps to set up Defects4J
----------------
1. Clone Rbugs:
    - `git clone https://github.com/kusumotolab/Rbugs`

2. Initialize Rbugs (download the project repositories):
    - `python3 Rbugs.py init`

Using Rbugs
================
#### Example commands
1. Checkout a buggy source code version (dplyr, bug 1, buggy version):
    - `python3 Rbugs.py checkout dplyr 1b`

2. Install dependencies and run tests:
    - `python3 Rbugs.py install-deps dplyr 1b`
    - `python3 Rbugs.py test dplyr 1b`

Command-line interface
-----------------------
### checkout: checkout a buggy or a fixed project version
`python3 Rbugs.py checkout project_name bug_id`<br>
Checked out project version is in `bug_dir`.

### install-deps: install dependencies
`python3 Rbugs.py install-deps project_name bug_id`<br>
Use this command after `checkout`.

### test: run tests
`python3 Rbugs.py test project_name bug_id`<br>
Use this command after `checkout` and `install-deps`.