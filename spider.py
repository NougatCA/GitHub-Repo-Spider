import os
import requests
from subprocess import check_call


class GithubSpider(object):

    def __init__(self):

        self.out_dir = 'out/'
        self.repo_dir = 'repos/'
        self.log_dir = 'logs/'

        dirs = [self.out_dir, self.repo_dir, self.log_dir]
        for d in dirs:
            if not os.path.exists(d):
                os.makedirs(d)

        self.url = 'https://api.github.com/search/repositories?q=language:java&sort=stars'

        with open('auth.token', mode='r') as f:
            self.auth_token = f.readline()

        self.headers = {
            'Authorization': 'token {}'.format(self.auth_token),
            'Content-Type': 'application/json'
        }

    def requests_get(self, url):
        return requests.get(url, headers=self.headers)

    def page_iter(self):
        url = self.url
        while True:
            # request url
            print('\n------------------------------------------------------------')
            print('Requests url:', url)
            r = self.requests_get(url)
            assert r.status_code == 200

            repos = r.json()['items']
            for repo in repos:
                self.handle_repo(repo)

            # next page
            if 'next' not in r.links:
                break
            url = r.links['next']['url']

            break

    def handle_repo(self, repo):
        print('\n***************')
        print('repo:', repo['full_name'])
        print('stars:', repo['stargazers_count'])
        print('clone url:', repo['clone_url'])
        print('description:', repo['description'])

        if not self.contains_java(repo['trees_url']):
            print('This repo does not contain java file.')
            return

        check_call('git clone {}'.format(repo['clone_url']), shell=True, cwd='repos')

    def contains_java(self, tree_url):
        tree_url = tree_url.replace('{/sha}', '/master?recursive=1')
        r = self.requests_get(tree_url)
        # print(json.dumps(r.json(), indent=4, separators=(', ', ': ')))

        nodes = r.json()['tree']
        for node in nodes:
            path = node['path']
            path_type = node['type']

            if path.endswith('.java') and path_type == 'blob':
                # print('java file:', path)
                return True
        return False



if __name__ == '__main__':
    spider = GithubSpider()
    spider.page_iter()
