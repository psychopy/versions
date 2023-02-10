import subprocess

vers = ['2022.2.1', '2022.2.2']

for ver in vers:
    
    commands = [
        f'git checkout {ver}',
        f'git checkout -b {ver}fixes',
        f'mkdir psychopy/tests',
        f'cp /Users/lpzjwp/code/psychopy/git/psychopy/tests/__init__.py psychopy/tests',
        f'cp /Users/lpzjwp/code/psychopy/git/psychopy/tests/utils.py psychopy/tests',
        f'git add psychopy/tests/*',
        ['git', 'commit', '-m', "added missing test utils"],
        f'git push origin {ver}fixes',
        f'git tag {ver} -m "{ver}" --force',
        f'git push origin {ver} --force',    
    ]
    for command in commands:
        print("  - ", command)
        if type(command) == str:
            command = command.split()
        proc = subprocess.Popen(command)
        proc.communicate()
        if proc.stdout:
            print(proc.stdout)
        if proc.stderr:
            print(proc.stderr)
        if proc.returncode != 0:
            raise IOError('that call failed:', command)
    
#subprocess.check_output('git fetch github --tags'.split()).decode('UTF-8') 
# done '2021.2.3', '2022.1.0', '2022.1.1','2022.1.2','2022.1.4', '2022.2.0'