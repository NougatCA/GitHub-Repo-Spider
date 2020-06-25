
s = '1212432 res/fdasdf https://sdfadfg.dgadsg.asdgasd sdfa dfa d af'
repo_id, full_name, clone_url = s.strip().split(maxsplit=2)
print(repo_id)
print(full_name)
print(clone_url)
