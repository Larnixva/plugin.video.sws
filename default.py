#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import re
import urlparse
import pickle
import urllib
import json

import xbmcaddon
import xbmcplugin
import xbmcgui
import xbmcvfs

from bs4 import BeautifulSoup
import requests

addon_handle = int(sys.argv[1])
addon = xbmcaddon.Addon(id='plugin.video.sws')
addondir = xbmc.translatePath(addon.getAddonInfo('profile'))
xbox = xbmc.getCondVisibility("System.Platform.xbox")

baseurl					=				'https://www.stanwinstonschool.com/'
loginurl				= baseurl + 	'users/sign_in'
streamlisturl			= baseurl + 	'account/streams'
blogurl					= baseurl + 	'blog'

loc = addon.getLocalizedString
setting = addon.getSetting

params = urlparse.parse_qsl(sys.argv[2][1:])
params = dict(params)

def displayEmailDialog(start=''):
	emailb = xbmc.Keyboard()
	emailb.setHeading(loc(30001))
	emailb.setDefault(start)
	emailb.setHiddenInput(False)
	emailb.doModal()
	if emailb.isConfirmed():
		addon.setSetting('email', emailb.getText())

def displayPasswordDialog(start=''):
	passb = xbmc.Keyboard(heading=loc(30002), hidden=True)
	passb.setHeading(loc(30002))
	passb.setDefault(start)
	passb.setHiddenInput(True)
	passb.doModal()
	if passb.isConfirmed():
		addon.setSetting('password', passb.getText())

def displayDialogOk(message):
	d = xbmcgui.Dialog()
	d.ok('Stan Winston School', message)

def writeCookies(cookies):
	f = xbmcvfs.File(addondir + 'cookie.jar', 'w')
	pickle.dump(requests.utils.dict_from_cookiejar(cookies), f)
	f.close()
	#print 'Wrote: '+ str(requests.utils.dict_from_cookiejar(cookies))

def readCookies():
	if not xbmcvfs.exists(addondir + 'cookie.jar'):
		#print 'No/empty cookie.jar'
		return False
	else:
		f = xbmcvfs.File(addondir + 'cookie.jar', 'r')
		tmp = f.read()
		if not tmp:
			return False
		cookies = requests.utils.cookiejar_from_dict(pickle.loads(tmp))
		f.close()
		#print 'Read: ' + str(requests.utils.dict_from_cookiejar(cookies))
		return cookies

def auth(cookies):
	if not cookies:
		r = requests.get(loginurl)
		soup = BeautifulSoup(r.content)
		auth_token = str(soup.find(id='login_user').find(attrs={'name' : 'authenticity_token'})['value'])
		authdata = {
			'utf8'						:						u'\u2713',
			'authenticity_token'		:						auth_token,
			'user[email]'				:						str(setting('email')),
			'user[password]'			:						str(setting('password')),
			'user[vanilla]'				:						'0',
			'user[remember_me]'			:						'1'
		}
		r = requests.post(loginurl, authdata)
		soup = BeautifulSoup(r.content)
		namestring = soup.find(attrs={'class' : 'name'})
		if namestring:
			namestring = namestring.string.split(', ', 1)[1]
			cookies = r.cookies
			#print 'Auth successful (login)'
			return cookies
		else:
			displayDialogOk(loc(30003))
			displayEmailDialog(setting('email'))
			displayPasswordDialog(setting('password'))
			#print 'Auth not successful (login)'
	else:
		r = requests.get(baseurl, cookies=cookies)
		soup = BeautifulSoup(r.content)
		namestring = soup.find(attrs={'class' : 'name'})
		if not namestring:
			print 'Auth not successful (cookie)'
			cookies = False
			return auth(cookies)
	#print 'Auth successful (cookies)'
	return cookies

def makeUrl(params):
	#print 'URL: ' + sys.argv[0] + '?' + urllib.urlencode(params)
	return sys.argv[0] + '?' + urllib.urlencode(params)

def index(cookies):
	# auth stuff
	cookies = auth(cookies)
	writeCookies(cookies)

	li = xbmcgui.ListItem('Blogvideos####', iconImage='defaultfolder.png')
	params = {'mode' : 'showblogvideos'}
	xbmcplugin.addDirectoryItem(handle=addon_handle, url=makeUrl(params), listitem=li, isFolder=True)

	li = xbmcgui.ListItem('Tutorials####', iconImage='defaultfolder.png')
	params = {'mode' : 'showtuts'}
	xbmcplugin.addDirectoryItem(handle=addon_handle, url=makeUrl(params), listitem=li, isFolder=True)

	xbmcplugin.endOfDirectory(addon_handle)
	return cookies

def showBlogVideos(cookies, params={}):
	headers = {'Accept' : 'text/html'}
	r = requests.get(blogurl, cookies=cookies, headers=headers)		### /?page=xxx
	soup = BeautifulSoup(r.content)
	boxes = soup.find_all('iframe')
	print 'BLALBLALBLDFSDGSDGSGHSGSDFSDFDS------------------------------------------------------'
	print str(boxes)
	for box in boxes:
		src = box['src']
		print src
		vid = src.split('/')[-1].split('?')[0]
		print vid
		li = xbmcgui.ListItem(vid)
		li.setInfo('video', {'title' : vid})
		li.setProperty('isPlayable','true')
		if xbox==True:
			params = {'mode' : 'playvideo', 'url' : 'plugin://video/YouTube/?path=/root/video&action=play_video&videoid=' + vid, 'name' : vid}
		else:
			params = {'mode' : 'playvideo', 'url' : 'plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid=' + vid, 'name' : vid}
		xbmcplugin.addDirectoryItem(handle=addon_handle, url=makeUrl(params), listitem=li)
	xbmcplugin.endOfDirectory(addon_handle)

def showTuts(cookies, params={}):
	r = requests.get(streamlisturl, cookies=cookies)
	soup = BeautifulSoup(r.content)
	boxes = soup.find_all(attrs={'class' : 'stream_box'})
	for box in boxes:
		name = box.a.get_text(strip=True)
		exturl = box.a['href']
		li = xbmcgui.ListItem(name, iconImage='defaultfolder.png')
		params = {'mode' : 'showtutvideos', 'url' : exturl}
		xbmcplugin.addDirectoryItem(handle=addon_handle, url=makeUrl(params), listitem=li, isFolder=True)
	xbmcplugin.endOfDirectory(addon_handle)

def showTutVideos(cookies, params={}):
	r = requests.get(baseurl + params['url'][1:], cookies=cookies)
	soup = BeautifulSoup(r.content)
	scripts = soup.find_all('script')
	regex = re.compile(r'//<!\[CDATA\[\s+var\s+array\s+=\s+JSON.parse\(\'(.*)\'\)')
	for script in scripts:
		if script.text is not None:
			x = regex.match(script.text.strip(' \t\n\r'))
			if x:
				match = x.group(1)
				videoinfo = json.loads(str(match).replace('\\"', '"').replace('\\\'', '\''))
				picpath = ''
				#print videoinfo
				for i in videoinfo:
					if (i['first_frame_image'] is not '') and (picpath is ''):
						picpath = addondir + i['first_frame_image'].split('/')[-1].split('?')[0]
						dl = requests.get(baseurl + i['first_frame_image'])
						dlf = xbmcvfs.File(addondir + i['first_frame_image'].split('/')[-1].split('?')[0], 'wb')
						dlf.write(dl.content)
						dlf.close()
					li = xbmcgui.ListItem(i['title'])
					li.setIconImage(picpath)
					li.setThumbnailImage(picpath)
					li.setInfo('video', {'title' : i['title']})
					li.setProperty('isPlayable','true')
					params = {'mode' : 'playvideo', 'url' : i['video_hi_url'], 'pic' : picpath, 'name' : i['title']}
					xbmcplugin.addDirectoryItem(handle=addon_handle, url=makeUrl(params), listitem=li)
	xbmcplugin.endOfDirectory(addon_handle)

def playVideo(params={}):
	if not 'pic' in params:
		li = xbmcgui.ListItem(label=params['name'], iconImage='defaultvideo.png', thumbnailImage='defaultvideo.png', path=params['url'])
	else:
		li = xbmcgui.ListItem(label=params['name'], iconImage=params['pic'], thumbnailImage=params['pic'], path=params['url'])
	xbmcplugin.setResolvedUrl(handle=addon_handle, succeeded=True, listitem=li)

#main

if not setting('email'):
	displayEmailDialog()
if not setting('password'):
	displayPasswordDialog()

if 'mode' in params:
	cookies = readCookies()
	if params['mode'] == 'showtuts':
		showTuts(cookies, params)
	elif params['mode'] == 'showblogvideos':
		showBlogVideos(cookies, params)
	if params['mode'] == 'showtutvideos':
		showTutVideos(cookies, params)
	elif params['mode'] == 'playvideo':
		playVideo(params)
else:
	cookies = index(readCookies())
