import os
import requests
import logging
import time
import subprocess
import sys
import stat


class GithubSpider(object):

    def __init__(self, year):
        self.year = year

        self.repo_root = 'repos/{}/'.format(self.year)
        self.repo_dir = self.repo_root
        self.log_dir = 'logs/'

        dirs = [self.repo_dir, self.log_dir]
        for d in dirs:
            if not os.path.exists(d):
                os.makedirs(d)

        # logger
        self.logger = logging.getLogger()
        self.logger.setLevel(level=logging.INFO)
        handler = logging.FileHandler(os.path.join(self.log_dir,
                                                   time.strftime('%Y%m%d_%H%M%S', time.localtime())) +
                                      '{}.spider.log'.format(self.year),
                                      encoding='utf-8')
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.cloned_repo = None
        self.cloned_repo_id = set()
        if os.path.exists('cloned_repo.{}.txt'.format(self.year)):
            self.cloned_repo = open('cloned_repo.{}.txt'.format(self.year), mode='r+', encoding='utf-8')
            lines = self.cloned_repo.readlines()
            for line in lines:
                if line == '':
                    continue
                repo_id, _, _ = line.strip().split(maxsplit=2)
                self.cloned_repo_id.add(repo_id)
        else:
            f = open('cloned_repo.{}.txt'.format(self.year), mode='w', encoding='utf-8')
            f.close()
            self.cloned_repo = open('cloned_repo.{}.txt'.format(self.year), mode='r+', encoding='utf-8')

        self.cloned_year_month = open('cloned_year_month.txt', mode='a+', encoding='utf-8')

        self.url = 'https://api.github.com/search/repositories?' + \
                   'q=language:java+created:{}-{:02d}&sort=stars&per_page=100'

        with open('auth.token', mode='r') as f:
            self.auth_token = f.readline()

        self.headers = {
            'Authorization': 'token {}'.format(self.auth_token),
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' +
                          'AppleWebKit/537.36 (KHTML, like Gecko) ' +
                          'Chrome/83.0.4103.116 Safari/537.36 ' +
                          'Edg/83.0.478.56'
        }

        if sys.platform.startswith('win'):
            subprocess.check_call('git config --global core.longpaths true', shell=True, cwd='repos')

    def requests_get(self, url):
        return requests.get(url, headers=self.headers)

    def start_spider(self):
        for month in range(1, 13):
            self.repo_dir = os.path.join(self.repo_root, '{:02d}'.format(month))
            if not os.path.exists(self.repo_dir):
                os.makedirs(self.repo_dir)
            url = self.url.format(self.year, month)
            self.page_iter(url)
            self.cloned_year_month.write('{} {}\n'.format(self.year, month))
            self.cloned_year_month.flush()

        self.cloned_year_month.close()
        self.cloned_repo.close()

    def page_iter(self, url):
        break_flag = False
        while True:
            # request url
            print('\n------------------------------------------------------------')
            print('Requests url:', url)
            self.logger.info('Requests url: {}'.format(url))
            r = self.requests_get(url)
            assert r.status_code == 200

            repos = r.json()['items']
            for repo in repos:
                if repo['stargazers_count'] >= 100 and not repo['fork']:
                    self.handle_repo(repo)
                else:
                    break_flag = True
                    break

            # next page
            if 'next' not in r.links or break_flag:
                break
            url = r.links['next']['url']

    def handle_repo(self, repo):
        full_name = repo['full_name']
        stars_count = repo['stargazers_count']
        description = repo['description']
        clone_url = repo['clone_url']
        print('\n***************')
        print('repo:', full_name)
        print('stars:', stars_count)
        print('description:', description)
        print('clone url:', clone_url)
        self.logger.info('repo: {}, stars: {}, description: {}'.format(full_name, stars_count, description))
        self.logger.info('clone url: {}'.format(clone_url))

        repo_id = repo['id']
        if repo_id in self.cloned_repo_id:
            print('This repo already cloned.')
            self.logger.info('This repo already cloned.')
            return

        if not self.contains_java(repo['trees_url']):
            print('This repo does not contain java file.')
            self.logger.info('This repo does not contain java file.')
            return

        self.clone_repo(clone_url, repo_id, full_name, repo['name'])

    def contains_java(self, tree_url):
        tree_url = tree_url.replace('{/sha}', '/master?recursive=1')
        r = self.requests_get(tree_url)
        # print(json.dumps(r.json(), indent=4, separators=(', ', ': ')))

        if 'tree' not in r.json():
            print('Repo tree not found, clone directly.')
            self.logger.info('Repo tree not found, clone directly.')
            return True

        nodes = r.json()['tree']
        for node in nodes:
            path = node['path']
            path_type = node['type']

            if path.endswith('.java') and path_type == 'blob':
                # print('java file:', path)
                return True
        return False

    def clone_repo(self, clone_url, repo_id, full_name, name):
        print('Cloning repo...')
        retry_count = 0
        while True:
            try:
                return_code = subprocess.check_call('git clone {} {}/'.format(clone_url, name),
                                                    shell=True, cwd=self.repo_dir)
            except subprocess.CalledProcessError as e:
                print('Return code: ', e.returncode)
                print('Exception: ', e.output)
                self.logger.exception('[{}]: {}'.format(e.returncode, e.output))
                self.delete_dir(name)

                if retry_count == 5:
                    print('Clone failed. Skip this repo')
                    self.logger.error('Clone failed. Skip this repo')
                    break
                retry_count += 1
                print('Retrying...({}/5)'.format(retry_count))
            else:
                if return_code == 0:
                    print('Clone success.')
                    self.logger.info('Clone success.')
                    self.cloned_repo_id.add(repo_id)
                    self.cloned_repo.write('{} {} {}\n'.format(repo_id, full_name, clone_url))
                    self.cloned_repo.flush()

                    # delete repo files except java file
                    self.delete_repo_files(name)
                    print('Deleted non-java files.')
                    self.logger.info('Deleted non-java files.')

                    break
                else:
                    print('Unknown return code: {}, skip this repo.'.format(return_code))
                    self.logger.exception('Unknown return code: {}, skip this repo.'.format(return_code))
                    self.delete_dir(name)
                    break

    def delete_repo_files(self, repo_dir):
        # delete repo files except java file
        d = os.path.join(self.repo_dir, repo_dir)
        for root, _, files in os.walk(d):
            for file in files:
                if not file.endswith('.java'):
                    try:
                        os.chmod(os.path.join(root, file), stat.S_IWRITE)
                        os.remove(os.path.join(root, file))
                    except OSError:
                        self.logger.error('{} delete failed.'.format(os.path.join(root, file)))
        # clean empty dirs
        for root, dirs, files in os.walk(d, topdown=False):
            for item in dirs:
                d = os.path.join(root, item)
                try:
                    os.rmdir(d)
                except OSError:
                    continue

    def delete_dir(self, repo_dir):
        # delete repo dir
        d = os.path.join(self.repo_dir, repo_dir)
        if not os.path.exists(d):
            return
        for root, dirs, files in os.walk(d, topdown=False):
            for name in files:
                try:
                    os.chmod(os.path.join(root, name), stat.S_IWRITE)
                    os.remove(os.path.join(root, name))
                except OSError:
                    self.logger.error('{} delete failed.'.format(os.path.join(root, name)))
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except OSError:
                    self.logger.error('{} delete failed.'.format(os.path.join(root, name)))
        os.rmdir(d)


if __name__ == '__main__':
    for year in [2014, 2015, 2016, 2017, 2018]:
        spider = GithubSpider(year)
        spider.start_spider()
