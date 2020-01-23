from pkuthesis import ThesisDownloader

if __name__ == '__main__':
    downloader = ThesisDownloader('./chromedriver.exe')
    downloader.crawl_txt('./url.txt')
