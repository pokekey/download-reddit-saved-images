"""
Python script to download saved images from reddit
"""
from __future__ import print_function
import requests
import os
import re
import traceback
from glob import glob
from bs4 import BeautifulSoup as bs
from zipfile import ZipFile
from PIL import Image
import praw
try:
	from io import BytesIO
except ImportError:
	from StringIO import BytesIO
import time
import yaml


__author__ = 'Adrian Espinosa'
__version__ = '2.0.3'
__contributor__ = '/u/shaggorama'

IMAGE_FORMATS = ['bmp', 'dib', 'eps', 'ps', 'gif', 'im', 'jpg', 'jpe', 'jpeg',
				 'pcd', 'pcx', 'png', 'pbm', 'pgm', 'ppm', 'psd', 'tif',
				 'tiff', 'xbm', 'xpm', 'rgb', 'rast', 'svg']

CONFIG = open('config-mopaitai.yaml')
CONFIG_DATA = yaml.safe_load(CONFIG)
# user data
USERNAME = CONFIG_DATA['username']
PASSWORD = CONFIG_DATA['password']
SAVE_DIR = CONFIG_DATA['save_dir']
ALBUM_PATH = os.path.join(SAVE_DIR, 'albums')





class SavedPost(object):

	STATUS_PENDING = 0
	STATUS_SAVED = 1
	STATUS_EXCEPTION = 2
	STATUS_NOTDONE = 3

	def __init__(self, submission, save_dir):
		self.submission = submission
		self.save_dir = save_dir
		self.base_path = self._mk_base_path()
		self.saved_path = ""
		self.status_code = self.STATUS_PENDING
		self.error_message = ""


	def set_saved(self, saved_path):
		self.status_code = self.STATUS_SAVED
		self.saved_path = saved_path


	def set_exception(self, message):
		self.status_code = self.STATUS_EXCEPTION
		self.error_message = message

	def set_notdone(self, message):
		self.status_code = self.STATUS_NOTDONE
		self.error_message = message

		


	@property
	def is_saved(self):
		return self.status_code == self.STATUS_SAVED


	def _mk_base_path(self):
		if self.submission.subreddit.display_name == "goddesses":
			safeTitle = self.submission.title.replace("/", "").replace(" ", "").replace("\\", "").replace('"', "")
			path = os.path.join(self.save_dir, "{}_reddit_goddesss".format(safeTitle))
		else:
			safeTitle = self.submission.title.replace("/", "").replace(" ", "-").replace("\\", "").replace('"', "")
			safeTitle = re.sub("[/\\\[\]\?\"';,.@#$%^&*(){}|!]", "", safeTitle)
			author = ""
			authorRedditor = self.submission.author
			if authorRedditor is not None and authorRedditor.name is not None:
				author = "_" + self.submission.author.name
			path = os.path.join(self.save_dir, "r_{}{}_{}".format(self.submission.subreddit.display_name, author, safeTitle))
		return path





class Downloader(object):
	"""
	Downloader class.
	Define here all methods to download images from different hosts or
	even direct link to image
	"""
	# global ERRORS

	def __init__(self, saved_post):
		self.saved_post = saved_post
		self.submission = saved_post.submission
		self.album_path = os.path.join(self.saved_post.save_dir, 'albums')
		print("Downloading {} - {} ({})".format(self.submission.subreddit.display_name, self.submission.title, self.submission.url))

	def is_image_link(self, sub):
		"""
		Takes a praw.Submission object and returns a boolean
		describing whether or not submission links to an
		image.
		"""
		if sub.url.split('.')[-1] in IMAGE_FORMATS:
			return True
		else:
			return False

	def check_if_image_exists(self, path, is_file=True):
		"""
		Takes a path an checks whether it exists or not.
		param: is_file: Used to determine if its a full name
		(/Users/test.txt) or a pattern (/Pics/myphoto*)
		"""
		return os.path.isfile(path) if is_file else len(glob(path + '*')) >= 1

	def mk_unique_name(self, path):
		num = 1
		(p,e) = os.path.splitext(path)
		while os.path.exists(path):
			path = "{}_{:02d}{}".format(p, num, e)
			num += 1
		return path


	def download_and_save(self, url, custom_path=None):
		"""
		Receives an url.
		Download the image (bytes)
		Store it.
		"""

		response = requests.get(url)
		img = Image.open(BytesIO(response.content))
		img.verify()
		if not custom_path:
			path = self.saved_post.base_path + "." + img.format.lower()
		else:
			path = custom_path + "." + img.format.lower()
		path = self.mk_unique_name(path)
		Image.open(BytesIO(response.content)).save(path)
		self.saved_post.set_saved(path)
		print ("  > {}".format(path))


	def direct_link(self):
		"""
		Direct link to image
		"""
		try:
			self.download_and_save(self.submission.url)
		except Exception as ex:
			self.saved_post.set_exception(str(ex))
			traceback.print_exc()



	def imgur_album(self):
		"""
		Album from imgur
		"""
		download_url = 'http://s.imgur.com/a/%s/zip' % \
			(os.path.split(self.submission.url)[1])
		try:
			response = requests.get(download_url)
		except Exception as ex:
			self.saved_post.set_exception(str(ex))
			traceback.print_exc()
			return

		path = os.path.join(ALBUM_PATH, self.submission.title
							.encode('utf-8')[0:50].replace("/", ""))
		# extract zip
		if not os.path.exists(path):
			os.mkdir(path)
		try:
			# i = open(path + '.zip', 'w')
			# i.write(StringIO(response.content))
			# i.close()
			zipfile = ZipFile(BytesIO(response.content))
			zipfile.extractall(path)
			print ("  > {}".format(path))
			self.saved_post.set_saved(path)
		except Exception as ex:  # big album
			try:
				os.remove(path + '.zip')
			except OSError as ex:
				pass
			#print("Exception: {0}".format(str(ex)))
			print("  Album is too big, downloading images...")
			# this is the best layout
			idimage = os.path.split(self.submission.url)[1]
			if '#' in idimage:
				print("  (# in idimage)")
				idimage = idimage[0:idimage.index("#")]
			url = "http://imgur.com/a/%s/layout/blog" % (idimage)

			response = requests.get(url)
			soup = bs(response.content)
			container_element = soup.find("div", {"id": "image-container"})
			try:
				imgs_elements = container_element.findAll("a",
														  {"class": "zoom"})
			except Exception as ex:
				self.saved_post.set_exception(str(ex))
				return
			counter = 0
			for img in imgs_elements:
				counter
				img_url = img.attrs['href']
				try:
					# damn weird links
					if img_url.startswith('//'):
						img_url = "http:{0}".format(img_url)
					print("    {0}".format(img_url))
					self.download_and_save(img_url, custom_path=path +
										   "/" + str(counter))
				except Exception as ex:
					self.saved_post.set_exception(str(ex))
					traceback.print_exc()
					return
				counter += 1

	def imgur_link(self):
		"""
		Image from imgur
		"""
		# just a hack. i dont know if this will be a .jpg, but in order to
		# download an image data, I have to write an extension
		new_url = "http://i.imgur.com/%s.jpg" % \
			(os.path.split(self.submission.url)[1])
		try:
			self.download_and_save(new_url)
		except Exception as ex:
			self.saved_post.set_exception(ex)
			traceback.print_exc()

	def tumblr_link(self):
		"""
		Tumblr image link
		"""
		response = requests.get(self.submission.url)
		soup = bs(response.content)
		# div = soup.find("div", {'class': 'post'})
		# if not div:
		#     div = soup.find("li", {'class': 'post'})
		img_elements = soup.findAll("img")
		for img in img_elements:
			if "media.tumblr.com/tumblr_" in img.attrs['src']:
				img_url = img.attrs['src']
				# img = div.find("img")
				# img_url = img.attrs["src"]
				try:
					self.download_and_save(img_url)
				except Exception as ex:
					self.saved_post.set_exception(ex)
					traceback.print_exc()

	def flickr_link(self):
		"""
		Flickr image link
		"""
		response = requests.get(self.submission.url)
		soup = bs(response.content)
		div_element = soup.find("div", {"class": "photo-div"})
		img_element = div_element.find("img")
		img_url = img_element.attrs['src']
		try:
			self.download_and_save(img_url)
		except Exception as ex:
			self.saved_post.set_exception(ex)
			traceback.print_exc()

	def picsarus_link(self):
		"""
		Picsarus image link
		"""
		try:
			self.download_and_save(self.submission.url + ".jpg")
		except Exception as ex:
			self.saved_post.set_exception(ex)
			traceback.print_exc()

	def picasaurus_link(self):
		"""
		Picasaurus image link
		"""
		response = requests.get(self.submission.url)
		soup = bs(response.content)
		img = soup.find("img", {"class": "photoQcontent"})
		img_url = img.attrs['src']
		try:
			self.download_and_save(img_url)
		except Exception as ex:
			self.saved_post.set_exception(ex)
			traceback.print_exc()

	def choose_download_method(self):
		"""
		This method allows to decide how to process the image
		"""
		if self.is_image_link(self.submission):
			self.direct_link()
		else:
			# not direct, read domain
			if 'imgur' in self.submission.domain:
				# check if album
				if '/a/' in self.submission.url:
					self.imgur_album()
				else:
					self.imgur_link()
			elif 'tumblr' in self.submission.domain:
				self.tumblr_link()
			elif 'flickr' in self.submission.domain:
				self.flickr_link()
			elif 'picsarus' in self.submission.domain:
				self.picsarus_link()
			elif 'picasaurus' in self.submission.domain:
				self.picasaurus_link()
			else:
				self.saved_post.set_notdone("Domain '{}' not supported".format(self.submission.domain))


def save_posts(save_dir, limit=0, is_unsave=True):
	R = praw.Reddit("bot1")
	print("Logging in...")
	# create session
	print (R.user.me())
	print("Logged in.")
	print("Getting data...")
	# this returns a generator
	red = R.redditor(USERNAME)
	saved_posts = [ SavedPost(x, save_dir) for x in red.saved(limit=None) ]
	print ("{} posts found".format(len(saved_posts)))

	count = 0
	for sp in saved_posts:
		# delete trailing slash
		if sp.submission.url.endswith('/'):
			sp.submission.url = sp.submission.url[0:-1]
		# create object per submission. Trusting garbage collector!
		d = Downloader(sp)
		d.choose_download_method()
		count += 1
		if limit > 0 and count >= limit:
			break

	print("{} processed.".format(count))

	# unsave items
	if is_unsave:
		for sp in saved_posts:
			if sp.is_saved:
				print("Unsaving {}".format(sp.submission.title))
				sp.submission.unsave()
				time.sleep(2)  # reddit's api restriction

	for sp in saved_posts:
		if not sp.is_saved:
			print ("{}: {} error {}".format(sp.submission.title, sp.status_code, sp.error_message))



# check if dir exists
if not os.path.exists(SAVE_DIR):
	os.mkdir(SAVE_DIR)
if not os.path.exists(os.path.join(SAVE_DIR, 'albums')):
	os.mkdir(ALBUM_PATH)

save_posts(SAVE_DIR)