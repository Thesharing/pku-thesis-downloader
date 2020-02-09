import atexit
import img2pdf
import os
import re
import requestium
from time import sleep
from tqdm import tqdm
from selenium.common.exceptions import TimeoutException

import platform

DRIVER_DEFAULT = './chromedriver.exe' if platform.system() == 'Windows' else './chromedriver'


class ThesisDownloader:

    def __init__(self, driver_path: str = DRIVER_DEFAULT,
                 output_path: str = './output',
                 temp_path: str = './temp',
                 interval: int = 2,
                 timeout: int = 15,
                 no_window: bool = False):
        options = {
            'arguments': [
                '--headless',
                '--window-size=1920,1080'
            ]
        } if no_window else {}

        if not os.path.isfile(driver_path):
            raise FileNotFoundError('Chrome driver not found at {}'.format(driver_path))

        self.session = requestium.Session(webdriver_path=driver_path,
                                          browser='chrome',
                                          default_timeout=timeout,
                                          webdriver_options=options)
        self.num_pattern = re.compile(r'\d+')
        self.url_pattern = re.compile(
            r'https?://(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_+.~#?&/=]*)')
        self.interval = interval
        self.output_path = output_path
        if not os.path.isdir(self.output_path):
            os.mkdir(self.output_path)
        self.temp_path = temp_path
        if not os.path.isdir(self.temp_path):
            os.mkdir(self.temp_path)
        atexit.register(self._quit)

    @property
    def driver(self):
        return self.session.driver

    def crawl(self, url):
        """
        Crawl one URL.
        :param url: URL address
        """
        if not self._check_url(url):
            print('URL not valid. Check if it starts with http/https: {}'.format(url))
            return
        try:
            title, total, url = self._access_page(url)
            self.session.transfer_driver_cookies_to_session()
            self._download_img(url, total)
            print('Generating PDF...')
            self._generate_pdf(title, total)
            self._clean()
            print('Successfully download {}.'.format(title))
        except TimeoutException:
            print('Thesis not found: {}.'.format(url))

    def crawl_list(self, url_list):
        """
        Crawl list of URLs.
        :param url_list: list of URLs
        :return:
        """
        for url in url_list:
            self.crawl(url)

    def crawl_txt(self, path):
        """
        Crawl list of URLs stored in txt file.
        :param path: path to txt file
        :return:
        """
        with open(path, 'r', encoding='utf-8') as f:
            for url in f.readlines():
                if len(url) > 0:
                    self.crawl(url)

    def _access_page(self, url):
        self.driver.get(url)
        self.driver.ensure_element_by_class_name('look')
        btn = self.driver.find_element_by_class_name('look')
        link = btn.find_element_by_tag_name('a')
        url = link.get_attribute('href')
        self.driver.get(url)
        self.driver.ensure_element_by_id('totalPages')
        title = self.driver.title
        total_pages = self.driver.find_element_by_id('totalPages')
        match = self.num_pattern.search(total_pages.text)
        total = int(match.group())
        self.driver.ensure_element_by_id('loadingBg0')
        bg = self.driver.find_element_by_id('loadingBg0')
        img = bg.find_element_by_tag_name('img')
        url = img.get_attribute('src')
        url = url.replace('00001.jpg', '{:0>5d}.jpg')
        return title, total, url

    def _download_img(self, url, total):
        pbar = tqdm(total=total)
        for i in range(1, total + 1):
            r = self.session.get(url.format(i))
            with open(os.path.join(self.temp_path, '{0}.jpg'.format(i)), 'wb') as f:
                f.write(r.content)
            pbar.set_description('Page {0} / {1}'.format(i, total))
            pbar.update(1)
            sleep(self.interval)

    def _generate_pdf(self, title, total):
        with open(os.path.join(self.output_path, './{0}.pdf'.format(title)), 'wb') as f:
            f.write(img2pdf.convert([os.path.join(self.temp_path, '{0}.jpg'.format(i))
                                     for i in range(1, total + 1)]))

    def _clean(self):
        for i in os.listdir(self.temp_path):
            if i.endswith('.jpg'):
                os.remove(os.path.join(self.temp_path, i))

    def _check_url(self, url):
        return self.url_pattern.fullmatch(url) is not None

    def _quit(self):
        self.session.driver.quit()

    def __del__(self):
        self._quit()
