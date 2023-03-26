import sys
import re
import subprocess
import shutil

def quit_lint(num_warnings: int):
    print(f"Checked {num_warnings} linter warnings, quitting now.")
    subprocess.run(["rm", "out.txt"])
    exit()

def rerun_lint(num_warnings: int, folder: str):
    print(f"Checked {num_warnings} linter warnings, re-running linter\n\n")
    lint_folder(folder)
    exit()

def prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings: int, folder: str):
    print("Would you like to use the suggested fix:")
    print(f"< {edit_line}")
    print("---")
    print(f"> {replace_line}")
    cont = input("y/n: ")
    if cont == "y":
        lines[line_num - 1] = replace_line
        f.seek(0)
        f.writelines(lines)
        f.truncate()
        print("Used suggested fix")
    elif cont == "q":
        quit_lint(num_warnings)
    elif cont == "r":
        rerun_lint(num_warnings, folder)
    else:
        print("Did not use suggested fix")
    print()

def process_warning(warning, num_warnings: int, folder: str):
    sepWarning = warning.split(" ")
    if len(sepWarning) < 2: return
    file_parts = sepWarning[0].split(":")
    if len(file_parts) < 4: return
    parts = sepWarning[1:]
    warn_str = " ".join(parts)
    edit_file = file_parts[0] 
    line_num, col_num = int(file_parts[1]), int(file_parts[2]) 
    if warn_str == "S1039: unnecessary use of fmt.Sprintf (gosimple)":
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            pattern = r'fmt\.Sprintf\("([^"]*)"\)'
            replace_line = re.sub(pattern, r'"\1"', edit_line)
            prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif re.match(r"^increment-decrement: should replace (.*) with (.*) \(revive\)$", warn_str) is not None:
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            searcher = re.search(r"^increment-decrement: should replace (.*) with (.*) \(revive\)$",  warn_str)
            replace_line = lines[line_num - 1].replace(searcher.group(1), searcher.group(2))
            prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif warn_str == "S1023: redundant `return` statement (gosimple)" or warn_str == "unreachable: unreachable code (govet)" or re.match(r"^ineffectual assignment to (.*) \(ineffassign\)$", warn_str) is not None:
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            replace_line = ""
            prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif re.match( r"^string `(.*)` has [0-9]+ occurrences, but such constant `(.*)` already exists \(goconst\)$", warn_str) is not None:
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            searcher = re.search(r"^string `(.*)` has [0-9]+ occurrences, but such constant `(.*)` already exists \(goconst\)$", warn_str)
            replace_line = lines[line_num - 1].replace(f'"{searcher.group(1)}"', searcher.group(2))
            prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif warn_str == "non-wrapping format verb for fmt.Errorf. Use `%w` to format errors (errorlint)":
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            if edit_line[col_num - 6: col_num + 11] == '%s", err.Error())' or edit_line[col_num - 6: col_num + 11] == '%v", err.Error())':
                replace_line = edit_line[: col_num - 6] + '%w", err)' + edit_line[col_num + 11:]
                prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
            if edit_line[col_num - 6: col_num + 3] == '%s", err)' or edit_line[col_num - 6: col_num + 3] == '%v", err)':
                replace_line = edit_line[: col_num - 6] + '%w", err)' + edit_line[col_num + 3:]
                prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
            if edit_line[col_num - 7: col_num + 3] == '%+v", err)':
                replace_line = edit_line[: col_num - 7] + '%w", err)' + edit_line[col_num + 3:]
                prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
            if edit_line[col_num - 7: col_num + 11] == '%+v", err.Error())':
                replace_line = edit_line[: col_num - 7] + '%+v", err.Error())' + edit_line[col_num + 11:]
                prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif re.match(r"comparing with (!=|==) will fail on wrapped errors. Use errors.Is to check for a specific error \(errorlint\)", warn_str) is not None:
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            comp_errs = re.findall(r"err(\S*) (!=|==) (\S+)", edit_line)
            for (err_part, comp, err) in comp_errs:
                if err == "nil": continue
                replace_line = edit_line.replace(f"err{err_part} {comp} {err}", f"{'!' if comp == '!=' else ''}errors.Is(err{err_part}, {err})")
                prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif re.match(r"^copylocks: (.*) copies lock( value)?: (.*) contains sync.Mutex \(govet\)$", warn_str) is not None or re.match(r"^copylocks: (.*) passes lock by value: (.*) contains sync.Mutex \(govet\)$", warn_str) is not None:
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            replace_line = edit_line[:-1] + " //nolint:govet // keep existing behaviour\n"
            prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif re.match(r"^Error return value of `(.*)` is not checked \(errcheck\)$", warn_str) is not None:
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            func_call = re.search(r"^\s+(.*)", edit_line).group(1)
            if func_call[0:3] != 'go ':
                func_name = re.search(r"^Error return value of `(.*)` is not checked \(errcheck\)$", warn_str).group(1)
                placeholders = '_, _' if func_name in ['w.Write'] else '_'
                replace_line = edit_line.replace(func_call, f'{placeholders} = {func_call}')
                prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
            else:
                print("Would you like to use the suggested fix:")
                print(f"< {edit_line}")
                print("---")
                go_call = re.sub(r"go (.*)", "go func() {", edit_line)
                indent = re.search(r"(\s+)go", go_call).group(1)
                func_call = re.search(r"go (.*)", edit_line).group(1)
                print(f'> {go_call}', end='')
                print(f'> {indent}    _ = {func_call}\n', end='')
                print(f'> {indent}{"}()"}\n', end='')
                cont = input("y/n: ")
                if cont == "y":
                    lines[line_num - 1] = go_call
                    lines.insert(line_num, f'{indent}    _ = {func_call}\n')
                    lines.insert(line_num+1, f'{indent}{"}()"}\n')
                    f.seek(0)
                    f.writelines(lines)
                    f.truncate()
                    print("Used suggested fix")
                elif cont == "q":
                    quit_lint(num_warnings)
                elif cont == "r":
                    rerun_lint(num_warnings, folder)
                else:
                    print("Did not use suggested fix")
                print()
    elif warn_str == "Error return value is not checked (errcheck)":
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            if len(edit_line.split()) == 3: # handle type assertions
                parts = edit_line.split()
                replace_line = edit_line.replace(' '.join(parts), f'{parts[0]}, _ {parts[1]} {parts[2]}')
                prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
            else:
                func_call = re.search(r"^\s+(.*)", edit_line).group(1)
                replace_line = edit_line.replace(func_call, f'_ = {func_call}')
                prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif re.match(r"^var-naming: (.*) (.*) should be (.*) \(revive\)$", warn_str) is not None:
        var_name = re.search(r"^var-naming: (.*) (.*) should be (.*) \(revive\)$", warn_str).group(3)
        subprocess.run("pbcopy", text=True, input=var_name)
        print(f"Copied {var_name} to clipboard to replace all occurences\n")
    elif re.match(r"^(.*) `(.*)` is unused \(unused\)$", warn_str):
        type_name = re.search(r"^(.*) `(.*)` is unused \(unused\)$", warn_str).group(1)
        if type_name in ['var', 'const']:
            with open(edit_file, "r+") as f:
                lines = f.readlines()
                edit_line = lines[line_num - 1]
                replace_line = ""
                prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif re.match(r"^`(.*)` - `(.*)` is unused \(unparam\)$", warn_str) is not None:
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            unused_var = re.search(r"^`(.*)` - `(.*)` is unused \(unparam\)$", warn_str).group(2)
            replace_line = edit_line.replace(unused_var, '_')
            prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif re.match(r"^exported: type name will be used as (.*) by other packages, and that stutters; consider calling this (.*) \(revive\)$", warn_str) is not None:
        var_name = re.search(r"^exported: type name will be used as (.*) by other packages, and that stutters; consider calling this (.*) \(revive\)$", warn_str).group(2)
        subprocess.run("pbcopy", text=True, input=var_name)
        print(f"Copied {var_name} to clipboard to replace all occurences\n")
    elif re.match(r"^error-strings: error strings should not be capitalized or end with punctuation or a newline \(revive\)$", warn_str) is not None:
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            err_strs = re.findall(r"\(\"([^\"]+)\"", edit_line)
            for err_str in err_strs:
                replace_line = edit_line.replace(err_str, err_str[0].lower() + err_str[1:].rstrip(".!?"))
                prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif re.match(r"^S1011: should replace loop with `(.*)` \(gosimple\)$", warn_str):
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            loop_open = lines[line_num - 1]
            loop_body = lines[line_num]
            loop_close = lines[line_num + 1]
            loop_replace = re.search(r"^S1011: should replace loop with `(.*)` \(gosimple\)$", warn_str).group(1)
            replace_line = re.sub(r"for (.*) {", loop_replace, loop_open)
            print("Would you like to use the suggested fix:")
            print(f"< {loop_open}", end='')
            print(f"< {loop_body}", end='')
            print(f"< {loop_close}", end='')
            print("---")
            print(f"> {replace_line}")
            cont = input("y/n: ")
            if cont == "y":
                lines[line_num - 1] = replace_line
                del lines[line_num]
                del lines[line_num]
                f.seek(0)
                f.writelines(lines)
                f.truncate()
                print("Used suggested fix")
            elif cont == "q":
                quit_lint(num_warnings)
            elif cont == "r":
                rerun_lint(num_warnings, folder)
            else:
                print("Did not use suggested fix")
            print()
    elif warn_str == "SA1019: grpc.WithInsecure is deprecated: use WithTransportCredentials and insecure.NewCredentials() instead. Will be supported throughout 1.x. (staticcheck)":
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            replace_line = edit_line.replace("grpc.WithInsecure()", "grpc.WithTransportCredentials(insecure.NewCredentials())")
            prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif re.match(r"^`(.*)` is a misspelling of `(.*)` \(misspell\)$", warn_str) is not None:
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            spellings = re.search(r"^`(.*)` is a misspelling of `(.*)` \(misspell\)$", warn_str)
            replace_line = edit_line.replace(spellings.group(1), spellings.group(2))
            prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif re.match(r"^SA1019: (.*)SetBackground is deprecated: This option has been deprecated in MongoDB version 4.2. \(staticcheck\)$", warn_str) is not None:
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            replace_line = edit_line[:-1] + " //nolint:staticcheck // still using < 4.2\n"
            prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif re.match(r"^S1002: should omit comparison to bool constant, can be simplified to `(.*)` \(gosimple\)", warn_str) is not None:
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            bad_comp = re.search(r" (.*) (!=|==) ([a-z]+)", edit_line)
            print(bad_comp.group(3))
            new_comp = re.match(r"^S1002: should omit comparison to bool constant, can be simplified to `(.*)` \(gosimple\)", warn_str).group(1)
            replace_line = edit_line.replace(f'{bad_comp.group(1)} {bad_comp.group(2)} {bad_comp.group(3)}', new_comp)
            prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)    
    elif re.match(r"^unused-parameter: parameter '(.*)' seems to be unused, consider removing or renaming it as _ \(revive\)$", warn_str) is not None:
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            unused_var = re.search(r"^unused-parameter: parameter '(.*)' seems to be unused, consider removing or renaming it as _ \(revive\)$", warn_str).group(1)
            replace_line: str = ''
            if ' '+unused_var+' ' in edit_line:
                replace_line = edit_line.replace(' '+unused_var+' ', ' _ ')
            elif '('+unused_var+' ' in edit_line:
                replace_line = edit_line.replace('('+unused_var+' ', '(_ ')
            prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif re.match(r"^S1030: should use (.*) instead of (.*) \(gosimple\)$", warn_str) is not None:
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            cont = re.search(r"^S1030: should use (.*) instead of (.*) \(gosimple\)$", warn_str)
            replace_line = edit_line.replace(cont.group(2), cont.group(1))
            prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif warn_str == "errorf: should replace errors.New(fmt.Sprintf(...)) with fmt.Errorf(...) (revive)":
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            replace_line =re.sub(r"errors.New\(fmt.Sprintf\((.*)\)\)", r'fmt.Errorf(\1)', edit_line)
            prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif re.match(r"^var-declaration: should omit type (.*) from declaration of var (.*); it will be inferred from the right-hand side \(revive\)$", warn_str) is not None:
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            cont = re.search(r"^var-declaration: should omit type (.*) from declaration of var (.*); it will be inferred from the right-hand side \(revive\)$", warn_str)
            replace_line = edit_line.replace(cont.group(1)+' ', '')
            prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif re.match(r"^var-declaration: should drop (.*) from declaration of var (.*); it is the zero value \(revive\)$", warn_str) is not None:
        with open(edit_file, "r+") as f:
            lines = f.readlines()
            edit_line = lines[line_num - 1]
            cont = re.search(r"^var-declaration: should drop (.*) from declaration of var (.*); it is the zero value \(revive\)$", warn_str)
            replace_line = edit_line.replace(cont.group(1), '')
            prompt_suggestion(f, lines, line_num, edit_line, replace_line, num_warnings, folder)
    elif re.match(r"^error-naming: error var (.*)Err should have name of the form errFoo \(revive\)$", warn_str) is not None:
        name_part = re.search(r"^error-naming: error var (.*)Err should have name of the form errFoo \(revive\)$", warn_str).group(1)
        err_name = f'err{name_part[0].upper() + name_part[1:]}'
        subprocess.run("pbcopy", text=True, input=err_name)
        print(f"Copied {err_name} to clipboard to replace all occurences\n")

def warnings_in_file(f):
    warnings = []
    cur_warning = ""
    lines = f.readlines()
    for line in lines:
        if re.match(r"^[a-zA-Z0-9_\-\\/]+\.go:[0-9]+:", line) is not None:
            if cur_warning != "": warnings.append(cur_warning)
            cur_warning = ""
        cur_warning += line
    if len(warnings) == 0 and cur_warning != "": warnings.append(cur_warning)
    return warnings

def lint_folder(folder):
    num_warnings=0
    subprocess.run(f"golangci-lint run {folder} > out.txt", shell=True)
    with open("out.txt", "r") as f:
        warnings = warnings_in_file(f)
        warnings.sort()
        print(f"Found {len(warnings)} warnings\n")
        for w in warnings:
            num_warnings += 1
            parts = w.strip().split("\n")
            print(f"{'-' * 20}\n")
            print(f"Warning {num_warnings}\n")
            for p in parts: print(f"{p}")
            print(f"{'-' * 20}\n")
            file_location = parts[0].split(" ")[0][:-1]
            file_parts = file_location.split(":")
            if shutil.which("code") is not None:
                subprocess.run(f"code --goto {file_location}", shell=True)
            elif shutil.which("goland") is not None:
                subprocess.run(f"goland --line {file_parts[1]} {file_parts[0]}", shell=True)
            else:
                subprocess.run(f'vim "+call cursor({file_parts[1]}, {file_parts[2]})" {file_parts[0]}', shell=True)
            process_warning(parts[0], num_warnings, folder)
            cont = input("enter to continue: ")
            if cont == "q":
                quit_lint(num_warnings)
            if cont == "r":
                rerun_lint(num_warnings, folder)
            print()
    subprocess.run(f"golangci-lint run {folder} > out.txt", shell=True)
    with open("out.txt", "r") as f:
        if len(warnings_in_file(f)) > 0:
            print(f"Checked {num_warnings} linter warnings, running golangci-lint run {folder} again\n")
            lint_folder(folder)
        else:
            print(f"Checked {num_warnings} linter warnings, golangci-lint is happy!")
            subprocess.run(["rm", "out.txt"])

def show_usage():
    print()
    print("Must have golangci-lint and python3 installed. See https://golangci-lint.run/usage/install/#local-installation and https://www.python.org/downloads/")
    print()
    print("Usage: python3 linter.py [path [c, count, -c, --count]] [diff] [v, version, -v, --version] [h, help, -h, --help] ")
    print()
    print("`path` is the path to the folder you want to lint. Use `.` for the current folder")
    print()
    print("`count` shows the number of linter warnings in the file")
    print()
    print("`diff` shows the linter warning diff of the current branch to master")
    print()
    print("Enter `q` to quit the linter")
    print()
    print("Enter `r` to re-run the linter")
    print()
    print("You must re-run the linter after making an edit that changes the number of lines in a file")
    print()
    exit()

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ["h", "help", "-h", "--help"]:
        show_usage()
    elif sys.argv[1] in ["v", "version", "-v", "--version"]:
        subprocess.run(f"golangci-lint version", shell=True)
        exit()
    elif sys.argv[1] == "diff":
        cur_branch = subprocess.check_output("git rev-parse --abbrev-ref HEAD", shell=True).decode("utf-8").strip()
        cur_warnings, main_warnings = [], []
        subprocess.run(f"golangci-lint run > out.txt", shell=True)
        with open("out.txt", "r") as f:
            cur_warnings = warnings_in_file(f)
            subprocess.run(["rm", "out.txt"])
        subprocess.run(f"git checkout -q main; golangci-lint run > out.txt; git checkout -q {cur_branch}", shell=True)
        with open("out.txt", "r") as f:
            main_warnings = warnings_in_file(f)
            subprocess.run(["rm", "out.txt"])
        warning_delta = len(cur_warnings) - len(main_warnings)
        print(f"{cur_branch}: {len(cur_warnings)}")
        print(f"main: {len(main_warnings)}")
        print(f"{cur_branch} has {warning_delta} {'more' if warning_delta >= 0 else 'less'} linter warnings than main")
    elif sys.argv[1] in ["c", "count", "-c", "--count"]:
        folder = sys.argv[2] if len(sys.argv) > 2 else ''
        subprocess.run(f"golangci-lint run {folder} > out.txt", shell=True)
        with open("out.txt", "r") as f:
            print(f"There are {len(warnings_in_file(f))} linter warnings in {folder if folder != '' else 'this folder'}")
            subprocess.run(["rm", "out.txt"])
    elif len(sys.argv) > 2 and sys.argv[2] in ["c", "count", "-c", "--count"]:
        subprocess.run(f"golangci-lint run {sys.argv[1]} > out.txt", shell=True)
        with open("out.txt", "r") as f:
            print(f"There are {len(warnings_in_file(f))} linter warnings in {sys.argv[1]}")
            subprocess.run(["rm", "out.txt"])
    else:
        lint_folder(sys.argv[1])
