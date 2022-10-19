"""
Python script to download saved images from reddit
"""
from __future__ import print_function
import requests
import os
URLimport sys
import re
import traceback
import shutil
import importlib.util
import urllib.parse
from glob import glob
from bs4 import BeautifulSoup as bs
from zipfile import ZipFile
#TODO:  remove from PIL import Image
import praw
try:
	from io import BytesIO
except ImportError:
	from StringIO import BytesIO
import time
import yaml
import json
import html



__author__ = 'Adrian Espinosa'
__version__ = '2.0.3'
__contributor__ = '/u/shaggorama'

IMAGE_FORMATS = ['bmp', 'dib', 'eps', 'ps', 'gif', 'im', 'jpg', 'jpe', 'jpeg',
				 'pcd', 'pcx', 'png', 'pbm', 'pgm', 'ppm', 'psd', 'tif',
				 'tiff', 'xbm', 'xpm', 'rgb', 'rast', 'svg']

VIDEO_FORMATS = ['mp4']

def is_image_link(url):
	"""
	Takes a praw.Submission object and returns a boolean
	describing whether or not submission links to an
	image.
	"""
	url_parts = urllib.parse.urlparse(url)
	return url_parts.path.split('.')[-1] in IMAGE_FORMATS

def is_video_link(url):
	"""
	Takes a praw.Submission object and returns a boolean
	describing whether or not submission links to an
	image.
	"""
	url_parts = urllib.parse.urlparse(url)
	return url_parts.path.split('.')[-1] in IMAGE_FORMATS



class DownloaderException(Exception):
	pass



class FileNamer(object):

	def __init__(self, yamlConfig):
		pass

	def name_for(self, submission):
		'''Make a base name based on properties of the submission such
		as title and posting user.
		Parameters:
			following - a list of user's we are following and want posts named primarily
						based on their name.
		'''
		def clean_name(name, space_replacement):
			# Replace space with specific replacement.
			nn = name.replace(" ", space_replacement)
			# strip non ascii.  Primarily, this removes emoji which appear in many titles.
			ann = nn.encode('ascii', 'ignore').decode('ascii')
			# Remove the fussy punctuation
			ann = re.sub("[/\\\[\]\"';,.@#$%^&*(){}|!\?]", "", ann)
			# Remove some charactes from end of string.
			ann = re.sub("[_~-]+$", "", ann)
			return ann

		# Get author.  There may not be one.
		author = ""
		authorRedditor = self.submission.author
		if authorRedditor is not None and authorRedditor.name is not None:
			author = self.submission.author.name
		file_name = ''


		# Normal case.
		file_name = clean_name("r_{}{}_{}".format(self.submission.subreddit.display_name, 
									"_" + author if author else "", self.submission.title), "-")

		# Join to save directory.
		return file_name


class SavedPost(object):
	'''A post saved by the user which we will try to download.
	'''

	# Status of each post
	STATUS_PENDING = 0			# Not yet tried
	STATUS_SAVED = 1			# Successful download
	STATUS_EXCEPTION = 2		# Exception during download
	STATUS_NOTDONE = 3			# Not done
	STATUS_ERROR = 4			# This code detected an error

	def __init__(self, submission, save_dir, namer):
		self.submission = submission
		self.save_dir = save_dir
		self.base_path = os.path.join(save_dir, namer.name_for(submission))
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

	def set_error(self, message):
		self.status_code = self.STATUS_ERROR
		self.error_message = message


	@property
	def is_saved(self):
		return self.status_code == self.STATUS_SAVED





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
		print("    Downloading {} - {} ({})".format(self.submission.subreddit.display_name, self.submission.title, self.submission.url))



	def _check_if_image_exists(self, path, is_file=True):
		"""
		Takes a path an checks whether it exists or not.
		param: is_file: Used to determine if its a full name
		(/Users/test.txt) or a pattern (/Pics/myphoto*)
		"""
		return os.path.isfile(path) if is_file else len(glob(path + '*')) >= 1

	def _mk_unique_name(self, path):
		num = 1
		(p,e) = os.path.splitext(path)
		while os.path.exists(path):
			path = "{}_{:02d}{}".format(p, num, e)
			num += 1
		return path


	# This version uses Pillow (PIL) image library to
	# create file extenion based on image type.
	# But most URL have type extension so this is one dependency I was able to remove.
	# def _download_and_save(self, url, file_base_path):
	# 	"""
	# 	Receives an url.
	# 	Download the image (bytes)
	# 	Store it.
	# 	"""
	# 	response = requests.get(url)
	# 	img = Image.open(BytesIO(response.content))
	# 	img.verify()
	# 	path = file_base_path + "." + img.format.lower()
	# 	path = self._mk_unique_name(path)
	# 	Image.open(BytesIO(response.content)).save(path)
	# 	self.saved_post.set_saved(path)
	# 	print ("  > {}".format(path))




	def _download_to_file(self, url, file_path_base, extension=None):
		if extension:
			if not extension.startswith('.'):
				extension = '.' + extension
		else:
			# Get extention from path
			urlParts = urllib.parse.urlparse(url)
			(p, extension) = os.path.splitext(urlParts.path)

		file_path = self._mk_unique_name(file_path_base + extension)
		

		# Initiate the request.  stream=True allows streaming reading
		# (and use of copyfileobj)
		rv = requests.get(url, stream=True)
		if rv.status_code != 200:
			self.saved_post.set_error("Request to {} returned code {}".format(url, rv.status_code))
			rv.close()
			print (f"   HTTP get returned {rv.status_code}")
			raise DownloaderException()
			
		print ("    Saved to {}".format(url, file_path))
		with open(file_path, 'wb') as f:
			rv.raw.decode_content = True
			shutil.copyfileobj(rv.raw, f)   
		rv.close()
		return file_path

	def download(self):
		pass




class DirectDownloader(Downloader):
	'''Download from a direct link to the media file.'''
	def download(self):
		"""
		Direct link to image
		"""
		try:
			file_path = self._download_to_file(self.submission.url, self.saved_post.base_path)
			self.saved_post.set_saved(file_path)
		except Exception as ex:
			self.saved_post.set_exception(str(ex))
			traceback.print_exc()


class ImagureAlbumDownloader():
	def download(self):
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
					self._download_to_file(img_url, os.path.join(path, str(counter)))
				except Exception as ex:
					self.saved_post.set_exception(str(ex))
					traceback.print_exc()
					return
				counter += 1
		self.saved_post.set_saved(path)


class ImagureLinkDownloader(Downloader):
	'''
        	<video poster="//i.imgur.com/ebQD4MQh.jpg"
                preload="auto"
                autoplay="autoplay"
                muted="muted"  loop="loop"
            webkit-playsinline></video>
            <div class="video-elements">
                <source src="//i.imgur.com/ebQD4MQ.mp4" type="video/mp4">
            </div>
 

	'''

	def _find_video_link(self, soup):
		divnode = soup.find_all('div', { 'class': 'video-elements' })
		if not divnode or len(divnode) == 0:
			return None
		srcnode = divnode[0].find_all('source')
		if not srcnode:
			return None
		return srcnode[0].attrs['src']

		

	def download(self):
		"""
		Image from imgur
		"""
		# just a hack. i dont know if this will be a .jpg, but in order to
		# download an image data, I have to write an extension
		r = requests.get(self.submission.url)
		soup = bs(r.text, features="html.parser")
		if self.submission.url.endswith('gifv'):
			media_url = self._find_video_link(soup)
		else:
			self.saved_post.set_error("Unknown Imagur link type")
			return		
		if not media_url:
			self.saved_post.set_error("Failed to find Imagur link")
			return

		media_url = "http:" + media_url
		try:
			file_path = self._download_to_file(media_url, self.saved_post.base_path)
			self.saved_post.set_saved(file_path)
		except Exception as ex:
			self.saved_post.set_exception(ex)
			traceback.print_exc()



class TumblrDownloader(Downloader):
	def download(self):
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
					self._download_to_file(img_url, self.saved_post.base_path)
				except Exception as ex:
					self.saved_post.set_exception(ex)
					traceback.print_exc()
		self.saved_post.set_saved(self.saved_post.base_path)


class FlickrDownloader(Downloader):
	def download(self):
		"""
		Flickr image link
		"""
		response = requests.get(self.submission.url)
		soup = bs(response.content)
		div_element = soup.find("div", {"class": "photo-div"})
		img_element = div_element.find("img")
		img_url = img_element.attrs['src']
		try:
			file_path = self._download_to_file(img_url, self.saved_post.base_path)
			self.saved_post.set_saved(file_path)
		except Exception as ex:
			self.saved_post.set_exception(ex)
			traceback.print_exc()

class RedgifsDownloader(Downloader):
	def download(self):
		"""
		Flickr image link
		"""
		response = requests.get(self.submission.url)
		soup = bs(response.content)
		element = soup.find("script", {"type": "application/ld+json"})
		if element is None:
			err = "redgifs failed to find script element"
			self.saved_post.set_error(err)
			print ("   " + err)
			return
		jobj = json.loads(element.text)
		if jobj is None:
			err = "redgifs failed to parse json"
			self.saved_post.set_error(err)
			print ("   " + err)
			return
		video = jobj['video']
		if video is None:
			err = "redgifs json had no 'video' element"
			self.saved_post.set_error(err)
			print ("   " + err)
			return
		img_url = html.unescape(video['contentUrl'])
		if img_url is None:
			err = "redgifs json had no 'contentUrl' element"
			self.saved_post.set_error(err)
			print ("   " + err)
			return
		try:
			file_path = self._download_to_file(img_url, self.saved_post.base_path)
			self.saved_post.set_saved(file_path)
		except Exception as ex:
			self.saved_post.set_exception(ex)
			traceback.print_exc()

class PicsarusDownloader(Downloader):
	def download(self):
		"""
		Picsarus image link
		"""
		try:
			file_path = self._download_to_file(self.submission.url + ".jpg")
			self.saved_post.set_saved(file_path)
		except Exception as ex:
			self.saved_post.set_exception(ex)
			traceback.print_exc()


class PicasaurusDownloader(Downloader):
	def download(self):
		"""
		Picasaurus image link
		"""
		response = requests.get(self.submission.url)
		soup = bs(response.content)
		img = soup.find("img", {"class": "photoQcontent"})
		img_url = img.attrs['src']
		try:
			file_path = self._download_to_file(img_url, self.saved_post.base_path)
			self.saved_post.set_saved(file_path)
		except Exception as ex:
			self.saved_post.set_exception(ex)
			traceback.print_exc()



class GyfcatDownloader(Downloader):
	def download(self):
		r = requests.get(self.submission.url)
		soup = bs(r.text, features="html.parser")

		# make tag.  Get the last component of URL.
		url_parts = urllib.parse.urlparse(self.submission.url)
		parts = url_parts.path.split('/')
		vn = parts[-1]
		parts = vn.split('-')
		vn = parts[0]
		videotag = 'video-' + vn.lower()
		video_path = ""
		
		videonode = soup.find_all('video', id=videotag)
		if len(videonode) < 1:
			self.saved_post.set_error("gyfcat.com: failed to find 'video' node with tag '{}'".format(videotag))
			return
		if len(videonode) > 1:
			self.saved_post.set_error("gyfcat.com: found {} 'video' nodes with tag '{}'".format(len(videonode), videotag))
			return
			
		srcCount = 0
		print ("    Saving video to:")
		for videosource in videonode[0].find_all('source', type="video/mp4"):
			src_url = videosource.attrs['src']
			if not 'thumbs' in src_url:
				srcCount += 1
				base_path = self.saved_post.base_path + '_' + str(srcCount)
				video_path = self._download_to_file(src_url, base_path)
				if os.path.getsize(video_path) == 0:
					print ("ERROR:  zero size file")
					self.saved_post.set_error("File was zero size - not downloaded")
					return
					
		
		r.close()
		self.saved_post.set_saved(video_path)



def make_downloader(saved_post, is_expirmental=False):
	"""
	This method allows to decide how to process the image
	"""
	is_broken = False
	result = None
	if is_image_link(saved_post.submission.url):
		result = DirectDownloader(saved_post)
	else:
		# not direct, read domain
		if 'gfycat' in saved_post.submission.domain:
			result = GyfcatDownloader(saved_post)
		elif 'imgur' in saved_post.submission.domain:
			# check if album
			if '/a/' in saved_post.submission.url:
				result = ImagureAlbumDownloader(saved_post)
			else:
				result = ImagureLinkDownloader(saved_post)
		elif is_expirmental and 'redgifs' in saved_post.submission.domain:
			result = RedgifsDownloader(saved_post)
		elif is_expirmental and 'tumblr' in saved_post.submission.domain:
			result = TumblrDownloader(saved_post)
		elif is_expirmental and 'flickr' in saved_post.submission.domain:
			result = FlickrDownloader(saved_post)
		elif is_expirmental and 'picsarus' in saved_post.submission.domain:
			result = PicsarusDownloader(saved_post)
		elif is_expirmental and 'picasaurus' in saved_post.submission.domain:
			result = PicasaurusDownloader(saved_post)

	return result



def save_posts(R, username, save_dir, namer, limit=0, is_unsave=True, is_expirmental=False):
	print("Logging in...")
	# create session
	print (R.user.me())
	print("Logged in.")
	print("Getting data...")
	# this returns a generator
	red = R.redditor(username)
	saved_posts = [ SavedPost(x, save_dir, namer) for x in red.saved(limit=None) ]
	print ("{} posts found".format(len(saved_posts)))

	count = 0
	for sp in saved_posts:
		# delete trailing slash
		if sp.submission.url.endswith('/'):
			sp.submission.url = sp.submission.url[0:-1]
		print (sp.submission.url)
		# create object per submission. Trusting garbage collector!
		d = make_downloader(sp, is_expirmental=is_expirmental)
		if d is None:
			sp.set_notdone("Domain '{}' not supported".format(sp.submission.domain))
			continue
		d.download()
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
			print ("{1}: {2} - {0}".format(sp.submission.title, sp.status_code, sp.error_message))





CONFIG = open('config-mopaitai.yaml')
CONFIG_DATA = yaml.safe_load(CONFIG)
# user data
USERNAME = CONFIG_DATA['username']
PASSWORD = CONFIG_DATA['password']
CLIENT_ID = CONFIG_DATA['client_id']
CLIENT_SECRET = CONFIG_DATA['client_secret']
USER_AGENT = CONFIG_DATA['user_agent']
FOLLOWING = CONFIG_DATA['following']
SAVE_DIR = os.path.expanduser(CONFIG_DATA['save_dir'])
NAMER_MODULE = CONFIG_DATA['namer_module']

#
# Config file can name a different file namer. 
#
if NAMER_MODULE:
	# Load the module from the given file name and create a 
	# file namer object.
	spec = importlib.util.spec_from_file_location("namer", NAMER_MODULE)
	foo = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(foo)
	namer = foo.FileNamer(CONFIG_DATA)
else:
	namer = FileNamer(CONFIG_DATA)



# check if dir exists

if not os.path.exists(SAVE_DIR):
	print ("Save directory '{}' does not exist".format(SAVE_DIR))
	sys.exit(-1)

# Using configuration in praw.ini
#R = praw.Reddit("bot1")
R = praw.Reddit(user_agent=USER_AGENT, 
				client_id=CLIENT_ID, client_secret=CLIENT_SECRET, 
				password=PASSWORD, username=USERNAME)


# Download all known-working types.
save_posts(R, USERNAME, SAVE_DIR, namer, is_unsave=True, limit=0, is_expirmental=True)

# Test expirmental
#save_posts(R, USERNAME, SAVE_DIR, namer, is_unsave=True, limit=10, is_expirmental=True)

#save_posts(R, USERNAME, SAVE_DIR, namer, is_unsave=True, limit=1, is_expirmental=True)