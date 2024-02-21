import sys
import json
import re
import os
import shutil
import datetime
import subprocess
import glob
import requests
import psutil
import git

DIR_CONFIG = 'framework/config'
DIR_REPO = 'framework/repo'
DIR_GENERATED = 'framework/generated'
DIR_GITHUB_PKGS_REPO = 'framework/github_pkgs_repo'
DIR_LIB = 'framework/lib'
DIR_TMP = 'framework/tmp'
DIR_BUG_DIR = 'bug_dir'

PPM_URL = 'https://packagemanager.posit.co/cran/__linux__/'
#UBUNTU_CODE_NAME = 'jammy'     # Ubuntu22.04
UBUNTU_CODE_NAME = 'focal'      # Ubuntu20.04

OLDEST_PPM_SNAPSHOT_DATE = datetime.date(2017, 10, 10)
PKGBUILD_RELEASE_DATE = datetime.date(2018, 6, 27)
TESTTHAT3_RELEASE_DATE = datetime.date(2020, 10, 31)

#--------------------------------------------------------------------------------
# helpers

def parse_repo_name(uri):
    r = re.compile(r"^.+/(.+)(\.git)?")
    return r.match(uri).group(1)

def apply_repos(func, msg_prefix, *args):
    for uri in config["repos"]:
        print("### [%s]: %s" % (msg_prefix, parse_repo_name(uri)))
        func(uri)

def get_repo(uri):
    name = parse_repo_name(uri)
    repo = git.Repo("%s/%s/" % (DIR_REPO, name))
    return (repo, name)

def get_repo2(name):
    return git.Repo("%s/%s/" % (DIR_REPO, name))

def replace_troubleful_chars(message):
    return message.replace("\n", "<br>").replace("\r", "<br>").replace("\t", "<tab>")

def create_reader_config(fname):
    return open("%s/%s" % (DIR_CONFIG, fname), "r", encoding="UTF-8")

def create_reader_generated(fname):
    return open("%s/%s" % (DIR_GENERATED, fname), "r", encoding="UTF-8")

def create_reader_dir(dir, fname):
    return open("%s/%s" % (dir, fname), "r", encoding="UTF-8")

def create_writer_generated(fname):
    path = "%s/%s" % (DIR_GENERATED, fname)
    if os.path.exists(path):
        raise FileExistsError
    return open(path, "w", encoding="UTF-8")

def create_writer_dir_file(dir, fname):
    return open("%s/%s" % (dir, fname), "w", encoding="UTF-8")

def id2hex(name, id):
    id_num = id[0:len(id)-1]
    id_state = id[-1]

    fname = "hex-list-%s.txt" % name
    reader = create_reader_config(fname)

    for line in reader.read().splitlines():
        (id_list, hex_fix, hex_bug) = line.split(",")
        if id_list == id_num:
            if id_state == 'b':
                return hex_bug
            else:
                return hex_fix

def get_hex_pair(name, id):
    id_num = id[0:len(id)-1]
    id_state = id[-1]

    fname = "hex-list-%s.txt" % name
    reader = create_reader_config(fname)

    for line in reader.read().splitlines():
        (id_list, hex_fix, hex_bug) = line.split(",")
        if id_list == id_num:
            return(hex_fix, hex_bug)

def _flat_git(repo, hex, dir):
    if os.path.exists(dir): # use cache
        return

    repo.git.checkout(hex)
    repo.git.clean('-fdx')
    shutil.copytree(repo.git.working_dir, dir, ignore=shutil.ignore_patterns(".git*"), dirs_exist_ok=True)

def get_lib_path(name, id):
    return "%s/%s/%s/%s" % (sys.path[0], DIR_LIB, name, id)

def get_dir_path(name, id):
    return "%s/%s/%s/%s" % (sys.path[0], DIR_BUG_DIR, name, id)

def list2str(list):
    if not list:
        return '""'
    for i, val in enumerate(list):
        if i == 0:
            str = '"%s"' % val
        else:
            str = '%s, "%s"' % (str, val)
    return str

def get_current_time():
    DIFF_JST_FROM_UTC = 9
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=DIFF_JST_FROM_UTC)
    return now

def get_current_time_string():
    now = get_current_time()
    now_string = now.strftime("%Y-%m-%d %H:%M:%S")
    return now_string

def decode(str):
    if str is None:
        return ""
    return str.decode()

def delete_tmp():
    for p in glob.glob('%s/*' % DIR_TMP):
        shutil.rmtree(p, ignore_errors=True)

#--------------------------------------------------------------------------------
# load_config()

def load_config(path):
    global config
    f = open(path)
    config = json.load(f)

#--------------------------------------------------------------------------------
# cmd_init()

def make_dirs():
    os.makedirs(DIR_REPO, exist_ok=True)
    os.makedirs(DIR_GENERATED, exist_ok=True)
    os.makedirs(DIR_GITHUB_PKGS_REPO, exist_ok=True)
    os.makedirs(DIR_LIB, exist_ok=True)
    os.makedirs(DIR_TMP, exist_ok=True)
    os.makedirs(DIR_BUG_DIR, exist_ok=True)

def download_ppm_snapshot_list():
    url='https://packagemanager.rstudio.com/__api__/repos/2/transaction-dates'
    fname='ppm-snapshot-list.json'
    path = "%s/%s" % (DIR_GENERATED, fname)

    if os.path.exists(path): # use cache
        return

    urlData = requests.get(url).content
    with open(path ,mode='wb') as f:
        f.write(urlData)

def git_reset(uri):
    (repo, name) = get_repo(uri)
    repo.git.checkout('origin/HEAD')
    repo.git.clean('-fdx')

def git_clone(uri):
    os.chdir(DIR_REPO)
    try:
        git.Git().clone(uri)
    except git.exc.GitError as e:
        #git.Git().pull()
        if not ("already exists and is not an empty directory" in str(e)):
            raise e
    finally:
        os.chdir(sys.path[0])
        git_reset(uri)

def dump_git_commits(uri):
    (repo, name) = get_repo(uri)

    try:
        writer = create_writer_generated("log-%s.txt" % name)
    except FileExistsError:
        return # use cache

    for item in repo.iter_commits('HEAD'):
        file_list = list(item.stats.files.keys())
        message = replace_troubleful_chars(item.message)
        writer.write("%s\t%s\t%s\t%s\t%s\t%s\t%s\n"
                % (item.hexsha, item.author, item.authored_date, item.committer, item.committed_date, file_list, message))

def cmd_init():
    make_dirs()
    download_ppm_snapshot_list()
    apply_repos(git_clone, "git cloning")
    apply_repos(dump_git_commits, "dumping git commits")

#--------------------------------------------------------------------------------
# cmd_checkout()

def cmd_checkout(name, id):
    dir = get_dir_path(name, id)

    if os.path.exists(dir): # use cache
        return

    hex = id2hex(name, id)
    (hex_fix, hex_bug) = get_hex_pair(name, id)

    repo = get_repo2(name)
    _flat_git(repo, hex, dir)

    if hex == hex_bug:
        _flat_git(repo, hex_fix, "%s/%s" % (DIR_TMP, name))
        dir_from = "%s/%s/tests" % (DIR_TMP, name)
        dir_to = "%s/tests" % dir
        shutil.rmtree(dir_to, ignore_errors=True)
        try:
            shutil.copytree(dir_from, dir_to)
        except FileNotFoundError:
            delete_tmp()
            return
        delete_tmp()

#--------------------------------------------------------------------------------
# helpers for analyze_remotes_deps()

def get_remotes_list(dir):
    reader = create_reader_dir(dir, "DESCRIPTION")

    lines = reader.read()
    if "Remotes:" not in lines:
        return []

    lines_latter = lines.split('Remotes:')[1]
    lines_remotes_field = re.split('[^\t\n\r\f\v:]+:[^:]', lines_latter)[0].replace("\n", "").replace("\r", "").replace("\t", "").replace(" ", "")
    remotes_list = lines_remotes_field.split(',')
    return remotes_list

def get_commit_date_unix_epoch(name, tar_hex):
    reader = create_reader_generated("log-%s.txt" % name)

    for line in reader.read().splitlines():
        (hexsha, author, authored_date, committer, committed_date, files, message) = line.split("\t")
        if hexsha == tar_hex:
            return committed_date

def parse_package_name(package):
    if "/" in package:
        return package.split('@')[0].split('/')[1]
    else:
        return package.split('@')[0]

def package_list2package_name_list(list):
    return [package.split('@')[0].split('/')[1] if "/" in package else package.split('@')[0] for package in list]

def parse_package_hexsha(package):
    if "@" in package:
        return package.split('@')[1]
    else:
        return ""

#--------------------------------------------------------------------------------
# analyze_remotes_deps()

def change_description(dir, remotes_list, origin_name, id):
    reader = create_reader_dir(dir, "DESCRIPTION")
    lines = reader.read()
    reader.close()

    for package in remotes_list:
        package_name = parse_package_name(package)
        lines = lines.replace(package, "%s=local::%s/%s/%s/%s/%s" % (package_name, sys.path[0], DIR_GITHUB_PKGS_REPO, origin_name, id, package_name))

    writer = create_writer_dir_file(dir, "DESCRIPTION")
    writer.write(lines)

def get_hexsha_at_time(repo, date):
    name = parse_repo_name(repo.working_dir)
    reader = create_reader_generated("log-%s.txt" % name)

    for line in reader.read().splitlines():
        (hexsha, author, authored_date, committer, committed_date, files, message) = line.split("\t")
        if int(committed_date) < int(date):
            return hexsha

def _analyze_remotes_deps(dir, origin_name, commit_date, github_pkg_list, id):
    github_pkg_list_tmp = get_remotes_list(dir)

    if not github_pkg_list_tmp:
        return github_pkg_list

    change_description(dir, github_pkg_list_tmp, origin_name, id)

    for package in github_pkg_list_tmp:
        package_name = parse_package_name(package)
        github_pkg_name_list = package_list2package_name_list(github_pkg_list)
        if package_name in github_pkg_name_list:
            continue

        package_repo = get_repo2(package_name)

        if re.compile('.+/.+@.+').search(package):
            tar_hex = parse_package_hexsha(package)
        else:
            tar_hex = get_hexsha_at_time(package_repo, commit_date)
            package = "%s@%s" % (package, tar_hex)

        package_commit_dir = "%s/%s/%s/%s/%s" % (sys.path[0], DIR_GITHUB_PKGS_REPO, origin_name, id, package_name)
        _flat_git(package_repo, tar_hex, package_commit_dir)

        github_pkg_list.append(package)
        github_pkg_list = _analyze_remotes_deps(package_commit_dir, origin_name, commit_date, github_pkg_list, id)

    return github_pkg_list

def analyze_remotes_deps(name, id, dir):
    first_github_pkg_list = get_remotes_list(dir)

    if not first_github_pkg_list:
        return 0

    hex = id2hex(name, id)

    commit_date_unix_epoch = get_commit_date_unix_epoch(name, hex)
    github_pkg_list = []
    github_pkg_list = _analyze_remotes_deps(dir, name, commit_date_unix_epoch, github_pkg_list, id)

#--------------------------------------------------------------------------------
# make_lib()

def make_lib(name, id):
    os.makedirs("%s/%s/%s" % (DIR_LIB, name, id), exist_ok=True)

#--------------------------------------------------------------------------------
# install_pak()

def _install_pak_each_r_version_subproc(lib_path):
    msg_prefix = "install pak"
    cmd = 'R -e \'.libPaths("%s")\' -e \'options(repos=c(CRAN="%s%s/2023-08-28"))\' -e \'install.packages("pak")\'' % (lib_path, PPM_URL, UBUNTU_CODE_NAME)

    (returncode, stdout, stderr) = exec_subproc(cmd, msg_prefix)
    return (returncode, stdout, stderr)

def install_pak(name, id):
    lib_path = get_lib_path(name, id)
    _install_pak_each_r_version_subproc(lib_path)

#--------------------------------------------------------------------------------
# helpers(ppm)

def unix_epoch2ymd(commit_date_unix_epoch):
    return datetime.datetime.fromtimestamp(int(commit_date_unix_epoch), datetime.timezone.utc).date()

def load_ppm_snapshot_list():
    fname='ppm-snapshot-list.json'
    path = "%s/%s" % (DIR_GENERATED, fname)
    f = open(path)
    return json.load(f)

def get_ppm_snapshot_date_list():
    ppm_snapshot_list = load_ppm_snapshot_list()
    ppm_snapshot_date_list = []

    for i in range(len(ppm_snapshot_list)):
        ppm_snapshot_date_list.append(ppm_snapshot_list[i]["alias"])
    return ppm_snapshot_date_list

def _find_ppm_snapshot_date(date, ppm_snapshot_date_list):
    if date <= OLDEST_PPM_SNAPSHOT_DATE:
        return str(OLDEST_PPM_SNAPSHOT_DATE)

    if str(date) in ppm_snapshot_date_list:
        return str(date)
    else:
        return _find_ppm_snapshot_date(date + datetime.timedelta(days=-1), ppm_snapshot_date_list)

def find_ppm_snapshot_date(name, hex):
    commit_date_unix_epoch = get_commit_date_unix_epoch(name, hex)
    commit_date_ymd = unix_epoch2ymd(commit_date_unix_epoch)
    ppm_snapshot_date_list = get_ppm_snapshot_date_list()

    return _find_ppm_snapshot_date(commit_date_ymd, ppm_snapshot_date_list)

#--------------------------------------------------------------------------------
# install_basic_packages()

def _install_basic_packages_subproc(install_pkg_str, lib_path, ppm_snapshot_date_str):
    msg_prefix = "install-basic-package"
    cmd = 'R -e \'.libPaths("%s")\' -e \'options(repos=c(CRAN="%s%s/%s"))\' -e \'pak::pkg_install(c(%s), ask=FALSE)\'' % (lib_path, PPM_URL, UBUNTU_CODE_NAME, ppm_snapshot_date_str, install_pkg_str)

    (returncode, stdout, stderr) = exec_subproc(cmd, msg_prefix)
    return (returncode, stdout, stderr)

def install_basic_packages(name, id):
    lib_path = get_lib_path(name, id)
    hex = id2hex(name, id)
    ppm_snapshot_date_str = find_ppm_snapshot_date(name, hex)

    ppm_snapshot_date_split = ppm_snapshot_date_str.split('-')
    ppm_snapshot_date_ymd = datetime.date(int(ppm_snapshot_date_split[0]), int(ppm_snapshot_date_split[1]), int(ppm_snapshot_date_split[2]))
    if ppm_snapshot_date_ymd >= PKGBUILD_RELEASE_DATE:
        install_pkg_list = ["pkgbuild", "devtools"]
    else:
        install_pkg_list = ["devtools"]
    install_pkg_str = list2str(install_pkg_list)
    _install_basic_packages_subproc(install_pkg_str, lib_path, ppm_snapshot_date_str)

#--------------------------------------------------------------------------------
# install_deps()

def _install_deps_subproc(dir, lib_path, ppm_snapshot_date_str):
    msg_prefix = "install-deps"
    cmd = 'cd %s && R -e \'.libPaths("%s")\' -e \'options(repos=c(CRAN="%s%s/%s"))\' -e \'pak::local_install_dev_deps(upgrade=FALSE, ask=FALSE)\'' % (dir, lib_path, PPM_URL, UBUNTU_CODE_NAME, ppm_snapshot_date_str)

    (returncode, stdout, stderr) = exec_subproc(cmd, msg_prefix)
    return (returncode, stdout, stderr)

def install_deps(name, id, dir):
    lib_path = get_lib_path(name, id)
    hex = id2hex(name, id)
    ppm_snapshot_date_str = find_ppm_snapshot_date(name, hex)

    _install_deps_subproc(dir, lib_path, ppm_snapshot_date_str)

#--------------------------------------------------------------------------------
# cmd_install_deps()

def cmd_install_deps(name, id):
    lib_path = get_lib_path(name, id)
    if os.path.exists(lib_path): # use cache
        return

    dir = get_dir_path(name, id)
    if not os.path.exists(dir):
        print('Error: Please use \"checkout\" before \"install-deps\".')
        return

    analyze_remotes_deps(name, id, dir)
    make_lib(name, id)
    install_pak(name, id)
    install_basic_packages(name, id)
    install_deps(name, id, dir)

#--------------------------------------------------------------------------------
# cmd_test()

def _execute_tests_subproc(dir, lib_path):
    msg_prefix = "execute test"
    cmd = 'cd %s && R -e \'.libPaths("%s")\' -e \'devtools::test()\'' % (dir, lib_path)

    (returncode, stdout, stderr) = exec_subproc(cmd, msg_prefix)
    return (returncode, stdout, stderr)

def cmd_test(name, id):
    dir = get_dir_path(name, id)
    lib_path = get_lib_path(name, id)
    if not os.path.exists(dir) or not os.path.exists(lib_path):
        print('Error: Please use \"checkout\" and \"install-deps\" before \"test\".')
        return

    _execute_tests_subproc(dir, lib_path)

#--------------------------------------------------------------------------------
# exec_subproc()

def exec_subproc(cmd, msg_prefix=None, timeout_value=None):
    if msg_prefix is not None:
        now_string = get_current_time_string()
        print("### %s [%s subprocess]: start" % (now_string, msg_prefix))

    try:
        log = subprocess.run(cmd, shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            timeout=timeout_value)
    except subprocess.TimeoutExpired as e:
        for process in psutil.process_iter():
            if process.name() == "R":
                try:
                    process.terminate()
                except ProcessLookupError as e:
                    pass
        if msg_prefix is not None:
            now_string = get_current_time_string()
            print("### %s [%s subprocess]: timeout" % (now_string, msg_prefix))
        return (-1, '', 'timeout')

    print(decode(log.stdout))

    if msg_prefix is not None:
        now_string = get_current_time_string()
        print("### %s [%s subprocess]: end" % (now_string, msg_prefix))
    return (log.returncode, decode(log.stdout), decode(log.stderr))

#--------------------------------------------------------------------------------
# parse_args()

def check_args(args):
    if len(args) !=4:
        print('Error: Incorrect number of arguments.')
        exit()

    id_num = args[3][0:len(args[3])-1]
    id_state = args[3][-1]

    if re.fullmatch(r'[1-9]\d*', id_num) is None:
        print('Error: bug_id is <id>b or <id>f. <id> is an integer.')
        exit()

    if args[2] == 'dplyr':
        if int(id_num) < 1 or int(id_num) > 66:
            print('Error: bug_id is <id>b or <id>f. dplyr\'s <id> is from 1 to 66.')
            exit()
        if re.fullmatch(r'[bf]', id_state) is None:
            print('Error: bug_id is <id>b or <id>f.')
            exit()
    elif args[2] == 'ggplot2':
        if int(id_num) < 1 or int(id_num) > 87:
            print('Error: bug_id is <id>b or <id>f. ggplot2\'s <id> is from 1 to 87.')
            exit()
        if re.fullmatch(r'[bf]', id_state) is None:
            print('Error: bug_id is <id>b or <id>f.')
            exit()
    elif args[2] == 'tibble':
        if int(id_num) < 1 or int(id_num) > 19:
            print('Error: bug_id is <id>b or <id>f. tibble\'s <id> is from 1 to 19.')
            exit()
        if re.fullmatch(r'[bf]', id_state) is None:
            print('Error: bug_id is <id>b or <id>f.')
            exit()
    else:
        print('Error: \"%s\" is invalid project.' % args[2])
        exit()

def parse_args():
    args = sys.argv
    if len(args) <= 1:
        print('Error: Command not entered.')
        return

    if args[1] == 'init':
        cmd_init()
    elif args[1] == 'checkout':
        check_args(args)
        cmd_checkout(args[2], args[3])
    elif args[1] == 'install-deps':
        check_args(args)
        cmd_install_deps(args[2], args[3])
    elif args[1] == 'test':
        check_args(args)
        cmd_test(args[2], args[3])
    else:
        print('Error: \"%s\" is invalid command.' % args[1])
    return

#--------------------------------------------------------------------------------
# main()

if __name__ == '__main__':
    load_config("framework/config/config.json")
    parse_args()
