from git import Repo
from github import Github, Auth
import os

# using an access token
auth = Auth.Token(os.environ['PAT_GH'])

# Public Web Github
g = Github(auth=auth)

for pr in g.get_repo('liatrio/calvin-test-repo').get_pulls(state='open').get_page(0):
    print(pr.head.ref)
    repo = Repo('../cal-test-repo-2/')
    # if repo.git.checkout(pr.head.ref):
    #     repo.remotes.liatrio.fetch()
    #     repo.git.cherry_pick('--strategy=recursive', '-X', 'theirs', 'a7972f2')
    #     repo.git.add(all=True)
    #     repo.git.push()
    # else:
    repo.git.checkout('-b', pr.head.ref)
    repo.remotes.liatrio.fetch()
    repo.git.cherry_pick('--strategy=recursive', '-X', 'theirs', 'a7972f2')
    repo.git.add(all=True)
    repo.git.push()

# print(g.get_repo('liatrio/calvin-test-repo').get_pulls(state='open').get_page(0)[0].head.ref)

# repo = Repo('../cal-test-repo-2/')
# repo.git.checkout('full-test')
# repo.remotes.liatrio.fetch()
# repo.git.cherry_pick('--strategy=recursive', '-X', 'theirs', 'a7972f2')
# repo.git.add(all=True)
# repo.git.push()
