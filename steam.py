import itertools
import datetime
import requests
import glob
import re
import os

def now_to_filename( extension ) :

	return datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S') + '.' + extension

def download( source , raw = False , retry = 50 , timeout = 25 ) :

	for index in range(retry) :
		try :
			headers = {'User-Agent':'Mozilla/5.0'}
			cookies = {'wants_mature_content':'1','Steam_Language':'english','birthtime':'1000000000'}
			request = requests.get(source,headers = headers,cookies = cookies,timeout = timeout)
			if request.status_code != requests.codes.ok :
				request.raise_for_status()
			if raw :
				return request.content
			else :
				return request.content.decode('UTF-8')
		except requests.RequestException as error :
			print(type(error).__name__)

def re_any( pattern , text , flags = 0 , default = '' , group = 1 ) :

	try :
		return re.search(pattern,text,flags).group(group)
	except Exception :
		return default

def re_all( pattern , text , flags = 0 ) :

	return re.findall(pattern,text,flags)

def re_sub( pattern , value , text , flags = 0 ) :

	return re.sub(pattern,value,text,flags = flags)

def uopen( file , mode ) :

	return open(file,mode,encoding = 'UTF-8',newline = '\n')

def uread( file ) :

	with uopen(file,'r') as source : return source.read()

def usave( file , source ) :

	with uopen(file,'w') as output : output.write(source)

def APP2ID( source ) :

	return source.zfill(0x07)

def ID2APP( source ) :

	return source.lstrip('0')

def get_cache() :

	if os.path.exists('steam.txt') :
		return set(APP2ID(app) for app in uread('steam.txt').split())
	else :
		return set()

def set_cache( source ) :

	usave('steam.txt','\n'.join(sorted(set(APP2ID(app) for app in source))))

def create_css() :

	if not os.path.exists('steam.css') :
		css = ''
		css = css + 'body\n{\n\tbackground-color : #F0F0F0; font-family : monospace;\n}\n\n'
		css = css + 'table\n{\n\tmargin : auto;\n}\n\n'
		css = css + 'td\n{\n\tbackground-color : #FFFFFF; text-align : center; padding : 10px;\n}\n\n'
		css = css + '.grey { color : #BBBBBB; }\n'
		css = css + '.rose { color : #BB0000; }\n'
		css = css + '.mint { color : #00BB00; }\n'
		css = css + '.blue { color : #0000BB; }\n'
		css = css + '.dark { color : #000000; }'
		usave('steam.css',css)

def get_missing_icons() :

	if not os.path.exists('icons') :
		os.mkdir('icons')

	html_icons = set()

	for path in glob.glob('*.html') :
		html_icons.update(re_all('icons/([0-9]+).jpg',uread(path)))

	for icon,index in zip(html_icons,itertools.count(1)) :

		icon_uuid = ID2APP(icon)
		icon_file = 'icons/%s.jpg' % (icon)

		if os.path.exists(icon_file) :
			continue
		else :
			print('Download image: %05d %s' % (index,icon))

		icon_href = 'https://steamcdn-a.akamaihd.net/steam/apps/%s/header.jpg' % (icon_uuid)
		icon_data = download(icon_href,True)

		if icon_data :
			with open(icon_file,'wb') as stream : stream.write(icon_data)

def free_unused_icons() :

	html_icons = set()
	disk_icons = set()

	for path in glob.glob('*.html') :
		html_icons.update(re_all('icons/([0-9]+).jpg',uread(path)))

	for path in glob.glob('icons\*.jpg') :
		disk_icons.add(re_any('icons[\\\/]([0-9]+)\.jpg',path))

	for icon in disk_icons - html_icons :
		os.remove('icons/%s.jpg' % (icon))

def crawl( href , maximum = 0xFFFF , order = [] , stop = False ) :

	create_css()

	all_apps = get_cache()
	new_apps = set()

	app_amount = 0
	sub_amount = 0

	for index in itertools.count(1) :

		if index > maximum :
			break

		link = href % (index)
		page = download(link)

		apps = set(re_all('<a href="https://store.steampowered.com/app/([0-9]+)',page))
		subs = set(re_all('<a href="https://store.steampowered.com/sub/([0-9]+)',page))

		if not apps and not subs :
			break

		new_apps.update(uuid for uuid in apps if uuid not in all_apps)
		all_apps.update(apps)

		app_amount += len(apps)
		sub_amount += len(subs)

		print('%05d %02d %02d %05d %05d %05d' % (index,len(apps),len(subs),app_amount,sub_amount,len(new_apps)))

	if stop :
		input()

	html_cache = []

	for app,index in zip(new_apps,itertools.count(1)) :

		uuid = APP2ID(app)
		page = download('https://store.steampowered.com/app/%s' % (app))

		name = re_any('<div class="apphub_AppName">(.+?)</div>',page)
		rate = re_any('([0-9]+)% of the [0-9,]+ user reviews for this game are positive.',page,default = '0')
		tags = re_all('"tagid":[0-9]+,"name":"([^"]+?)"',page)

		no_reviews_flag = bool(re.search('No user reviews',page))
		not_scored_flag = bool(re.search('Need more user reviews to generate a score',page))
		no_release_flag = bool(re.search('<div class="game_area_comingsoon game_area_bubble">',page))

		rate = int(rate)

		if not_scored_flag :
			rate = -1
		if no_reviews_flag :
			rate = -2
		if no_release_flag :
			rate = -3

		tag_order = 0

		for group in order :
			if all(tag in tags for tag in group) :
				break
			tag_order += 1

		html_cache.append((tag_order,rate,uuid,tags))

		print('%05d of %05d' % (index,len(new_apps)),uuid,name)

	if html_cache :

		html = uopen(now_to_filename('html'),'w')

		html.write('<html><head><meta charset = UTF-8><link rel = stylesheet href = steam.css></head>')
		html.write('<body><table>\n')

		for tag_order,rate,uuid,tags in sorted(html_cache) :

			if rate >= 100 :
				rate = '99%'

			elif rate <= -3 :
				rate = '---'
			elif rate <= -2 :
				rate = '○○○'
			elif rate <= -1 :
				rate = '●●●'

			else :
				rate = '%02d%%' % (rate)

			tags = '<br>'.join(sorted(set(tag.strip() for tag in tags)))

			format = ''
			format = format + '<tr class = mint>'
			format = format + '<td><a href = https://store.steampowered.com/app/%s><img src = icons/%s.jpg></a></td>'
			format = format + '<td>%s</td><td>%s</td></tr>\n'

			html.write(format % (uuid,uuid,rate,tags))

		html.write('</table></body></html>')
		html.close()

		get_missing_icons()
		free_unused_icons()
		set_cache(all_apps)

	print('---------------------------------------------')
	print('%05d %05d' % (app_amount,sub_amount))
	print('---------------------------------------------')