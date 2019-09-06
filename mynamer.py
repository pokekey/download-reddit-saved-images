import re
import datetime



class FileNamer(object):
	def __init__(self, yamlConfig):
		self._following = yamlConfig['following']
		self._subusingnames = yamlConfig['subusingnames']
		self._names = yamlConfig['names']
		self._names_compact = [ x.replace(' ', '').lower() for x in self._names ]


	def _recognize_person_name(self, title, author, sub_name):
		title = title.lower()
		author = author.lower()
		sub_name = sub_name.lower()
		for i in range(len(self._names)):
			full_name = self._names[i].lower()
			compact_name = self._names_compact[i]
			if full_name in title or full_name in author or full_name in sub_name or \
				compact_name in title or compact_name in author or compact_name in sub_name:
				return self._names[i]
		return None

	def _posting_time(self, submission):
		try:
			d = datetime.datetime.fromtimestamp(submission.created)
		except:
			d = datetime.datetime.now()
		return d.strftime("%Y%m%d")


	def name_for(self, submission):
		'''Make a base name based on properties of the submission such
		as title and posting user.
		Parameters:
			following - a list of user's we are following and want posts named primarily
						based on their name.
		'''
		def clean_name(name, space_replacement="_"):
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
		authorRedditor = submission.author
		if authorRedditor is not None and authorRedditor.name is not None:
			author = submission.author.name

		sub_name = submission.subreddit.display_name

		post_title = submission.title

		
		file_name = ''

		person_name = self._recognize_person_name(post_title, author, sub_name)

		if person_name:
			safeTitle = person_name.replace(' ', '')
			file_name = clean_name("{}_r_{}_{}".format(safeTitle, sub_name, post_title))

		elif sub_name in self._subusingnames and len(post_title) > 2:
			# Postings to this sub-reddit use person name as title.
			safeTitle = clean_name(post_title, "")
			dateStr = self._posting_time(submission)
			file_name = clean_name("{}_r_{}_{}".format(safeTitle, sub_name, dateStr))
		
		elif author and author.lower() in self._following:
			# Is this a folllowed user?  
			if sub_name == 'u_' + author:
				# from own profile, don't incluide subreddit name.
				file_name = clean_name("u_{}_{}".format(author, post_title), "-")
			else:
				file_name = clean_name("u_{}_{}_{}".format(author, sub_name, post_title), "-")

		else:
			# Normal case.
			safeTitle = clean_name(post_title, "-")
			file_name = clean_name("r_{}{}_{}".format(sub_name, 
										"_" + author if author else "", safeTitle), "-")

		# Join to save directory.
		return file_name