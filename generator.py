import os
import time
import logging


class DatasetGenerator(object):

    def __init__(self, dataset_name=None):
        self.repo_dir = 'repos/'
        if not os.path.exists(self.repo_dir):
            raise IOError('Repo dir not found.')

        self.log_dir = 'logs/'
        self.java_file_dir = 'java_files/'

        dirs = [self.log_dir, self.java_file_dir]
        for d in dirs:
            if not os.path.exists(d):
                os.makedirs(d)

        # continue with the prev work
        if dataset_name:
            self.dataset_dir = 'dataset/{}/'.format(dataset_name)
        else:
            self.dataset_dir = 'dataset/{}/'.format(time.strftime('%Y%m%d_%H%M%S', time.localtime()))
            os.makedirs(self.dataset_dir)

        # logger
        self.logger = logging.getLogger()
        self.logger.setLevel(level=logging.INFO)
        handler = logging.FileHandler(os.path.join(self.log_dir,
                                                   time.strftime('%Y%m%d_%H%M%S', time.localtime())) + '.generator.log',
                                      encoding='utf-8')
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # record the finished repo
        self.finished_repo = None
        self.finished_repo_name = set()
        if os.path.exists(os.path.join(self.dataset_dir, 'finished_repo.txt')):
            self.finished_repo = open(os.path.join(self.dataset_dir, 'finished_repo.txt'),
                                      mode='r+', encoding='utf-8')
            lines = self.finished_repo.readlines()
            for line in lines:
                if line == '':
                    continue
                repo_name, _ = line.strip().split(maxsplit=1)
                self.finished_repo_name.add(repo_name)
        else:
            f = open(os.path.join(self.dataset_dir, 'finished_repo.txt'), mode='w', encoding='utf-8')
            f.close()
            self.finished_repo = open(os.path.join(self.dataset_dir, 'finished_repo.txt'),
                                      mode='r+', encoding='utf-8')

    def start_generate(self):
        for repo_name in os.listdir(self.repo_dir):
            if repo_name in self.finished_repo_name:
                print('Repo {} is generated, skip.'.format(repo_name))
                self.logger.info('Repo {} is generated, skip.'.format(repo_name))
                continue
            java_file_list = self.get_java_files(os.path.join(self.repo_dir, repo_name))
            for java_file in java_file_list:
                self.read_java_file(java_file)

    def get_java_files(self, root_dir):
        """
        get the java file list in given folder
        :param root_dir: root path
        :return: java file path list, starts with the root path
        """
        java_files = []
        for root, _, file_list in os.walk(root_dir):
            for file in file_list:
                if file.endswith('.java'):
                    java_files.append(os.path.join(root, file))
        # print(java_files)
        return java_files

    def read_java_file(self, java_file):
        self.logger.info('Reading java file: {}'.format(java_file))
        with open(java_file, mode='r', encoding='utf-8') as f:
            pass


if __name__ == '__main__':
    generator = DatasetGenerator()
    generator.start_generate()

