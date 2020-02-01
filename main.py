from pkuthesis import ThesisDownloader

if __name__ == '__main__':
    downloader = ThesisDownloader()
    downloader.crawl_txt('./url.txt')
