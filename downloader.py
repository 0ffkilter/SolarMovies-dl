import json
from fake_useragent import UserAgent
from html.parser import HTMLParser
import os, sys, requests, re, argparse, subprocess, shutil
from multiprocessing import Pool
from tqdm import tqdm

ua = UserAgent()
print (ua.chrome)

headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
         'Referer': 'https://cssspritegenerator.com',
         'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
         'Accept-Encoding': 'none',
         'Accept-Language': 'en-US,en;q=0.8',
         'Connection': 'keep-alive'}

cdn_url = "https://solarmoviez.ru/ajax/movie_embed/%s"
loadvid_cdn_url = "https://loadvid.online/player?fid=%s&page=embed"
solar_cdn_url = "https://n-adele.betterstream.co/abrplayback/%s"

url_pat = re.compile("/(\d+)")
loadvid_pat = re.compile("(https\:.*)\\\\\"\}.*")
manifest_abr_pat = re.compile("(https://.*)")
manifest_part_pat = re.compile("(seg-\d+.*)")
manifest_cdn_id_pat = re.compile("(.*)playlist")

def fetch_file(file_to_fetch):
        if os.path.exists(file_to_fetch[0]):
            return
        response = requests.get(file_to_fetch[1],
                                headers=headers,
                                stream=True)
        with open(file_to_fetch[0], "wb") as f:
            for chunk in response:
                f.write(chunk)

def download_file(meta):
    url = meta[0]
    folder_path = meta[1]
    file_name = meta[2]

    cdn_id = url_pat.findall(url)[0]

    cdn_data = requests.get(cdn_url % cdn_id, data=None, headers=headers)

    cdn_json = json.loads(cdn_data.text)

    loadvid_cdn_id = cdn_json["src"][cdn_json["src"].rindex('/') + 1:]

    loadvid_data = requests.get(loadvid_cdn_url % loadvid_cdn_id, data=None, headers=headers)

    manifest_abr_link = loadvid_pat.findall(loadvid_data.text)[0]

    manifest_abr_link = manifest_abr_link.replace("\\", "")

    manifest_abr_file = requests.get(manifest_abr_link, data=None, stream=True)

    manifest_link = manifest_abr_pat.findall(manifest_abr_file.content.decode("ascii"))[0]

    manifest_file = requests.get(manifest_link)

    parts = manifest_part_pat.findall(manifest_file.text)

    part_base_link = manifest_cdn_id_pat.findall(manifest_link)[0]

    if not os.path.exists(folder_path):
            os.makedirs(folder_path)

    files_to_fetch = []

    for p in parts:
        out_path = os.path.join(folder_path, p[:p.find("?")])
        files_to_fetch.append((out_path,
                              part_base_link + p))

    with open(os.path.join(folder_path, "_files.txt"), "w+") as f:
        f.write("\n".join(["file %s" % (p[0].replace("\\", "/")) for p in files_to_fetch]))

    with Pool(4) as p:
        with tqdm(total=len(files_to_fetch)) as pbar:
            for i, _ in tqdm(enumerate(
                             p.imap_unordered(fetch_file, files_to_fetch))):
                pbar.update()

    filelist = os.path.join(folder_path, "_files.txt")

    file_name = "season3_episode1.mp4"
    subprocess.call(["ffmpeg", "-f", "concat", "-safe", "0", "-i",
                     filelist, "-c:v", "copy", "-c:a", "copy",
                   "-bsf:a", "aac_adtstoasc", file_name])

if __name__ == "__main__":
    
    filename = sys.argv[1]

    with open(filename, 'r') as f:
        lines = f.read().split("\n")   

        lines = [l.split(" ") for l in lines]

        lines = [[l[0], "season_" + l[1], "episode_" + l[2]] for l in lines]

        with Pool(4) as p:
            with tqdm(total=len(lines)) as pbar:
                for i, _ in tqdm(enumerate(
                                 p.imap_unordered(download_file, lines))):
                    pbar.update()