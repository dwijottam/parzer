import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from sklearn import svm
from nltk.tag import StanfordPOSTagger
import sentence
import pickle, random
from sets import Set

LEFT = 0
SHIFT = 1
RIGHT = 2

class Parser(object):
	"""
	Abstract Class ( Interface ) for Parser
	"""
	def __init__(self):
		pass
	
	def train():
		raise NotImplementedError( "Should have implemented this" )

	def validate():
		raise NotImplementedError( "Should have implemented this" )

	def test():
		raise NotImplementedError( "Should have implemented this" )		

class SVMParser(Parser):
	"""
	Dependency parser based on yamada et al ( 2003 )
	"""
	def __init__(self, vocab, tags):
		Parser.__init__(self)
		self.vocab = vocab
		self.tags = tags
		self.st = StanfordPOSTagger("wsj-0-18-bidirectional-distsim.tagger")
		self.clf = {} # pickle.load( open( "svm2.p", "rb" ) )

	def complete_subtree(self, trees, child):
		for t in trees:
			if t.dependency == child.position:
				return False
		return True

	def estimate_train_action(self, trees, position):
		a = trees[position]
		b = trees[position + 1]
		if a.dependency == b.position and self.complete_subtree(trees, a):
				return RIGHT
		elif b.dependency == a.position and self.complete_subtree(trees, b):
				return LEFT
		else:
			return SHIFT


	def estimate_action(self, trees, position, extracted_features):
		left_pos_tag = self.left_pos( trees, position )
		n = len(self.vocab) + len(self.tags)
		temp_features = lil_matrix((1,n), dtype = bool)
		for i in extracted_features:
			temp_features[0,i] = True
		if left_pos_tag in self.clf:
			action_array = self.clf[left_pos_tag].predict( temp_features )
		else:
			action_array = self.clf["<UNKNOWN>"].predict( temp_features )
		return action_array[0]


	def take_action(self, trees, position, action):
		a = trees[position]
		b = trees[position + 1]
			
		if action == RIGHT:
			b.insert_right(a)
			trees[position + 1] = b
			trees.remove(a)
		elif action == LEFT:
			a.insert_left(b)
			trees[position] = a
			trees.remove(b)
		return trees

	def extract_features(self, trees, i):
		target_node = trees[i]
		if ((target_node.lex) in self.vocab):
			lex_index = self.vocab[(target_node.lex)]
		else:
			lex_index = self.vocab[("<UNKNOWN>")]
		
		if ( target_node.pos_tag in self.tags):
			tag_index = len(self.vocab) + self.tags[(target_node.pos_tag)]
		else:
			tag_index = len(self.vocab) + self.tags[("<UNKNOWN>")]
		return [lex_index, tag_index]

	def left_pos(self, trees, i):
		target_node = trees[i]
		return target_node.pos_tag

	def train(self, sentences):
		m = len(sentences)
		n = len(self.vocab) + len(self.tags)
		print m
		print n
		# train_x = lil_matrix((m, n), dtype=np.bool)
		train_x = {}
		train_y = {}
		features = {}
		clf = {}

		for s in sentences:
			trees = s.get_labeled_trees()
			# print "Original"
			# print s.trees
			i = 0
			no_construction = False
			while ( len(trees) > 0 ):
				if i == len(trees) - 1:
					if no_construction == True:
						break;
					# if we reach the end start from the beginning
					no_construction = True
					i = 0
				else:
					left_pos_tag = self.left_pos(trees, i)
					
					# extract features
					extracted_features = self.extract_features(trees, i)

					# estimate the action to be taken for i, i+ 1 target  nodes
					y = self.estimate_train_action(trees, i)

					if left_pos_tag in train_x:
						train_x[left_pos_tag].append( extracted_features )
						train_y[left_pos_tag].append( y )

					else:
						train_x[left_pos_tag] = [extracted_features]
						train_y[left_pos_tag] = [y]

					# execute the action and modify the trees
					if y!= SHIFT:
						trees = self.take_action(trees, i ,y)
						no_construction = False
					else:
						i += 1

		for lp in train_x:
			print lp
			print len(train_x[lp])
			temp_features = lil_matrix((len(train_x[lp]),n), dtype = bool)

			for i in range( 0, len(train_x[lp]) ):
				j, k = train_x[lp][i]
				temp_features[i,j]  = True
				temp_features[i,k] = True

			features[lp] = temp_features.tocsr()

			train_x[lp] = None
			n_classes = Set()
			for i in train_y[lp]:
				n_classes.add(i)
			if( len(n_classes) > 1 ):
				clf[lp] = svm.SVC(kernel='poly', degree=2)
				clf[lp].fit(features[lp], train_y[lp])

		self.clf = clf
		print "pickling"
		pickle.dump( clf , open( "svm2.p", "wb" ) )
		print "pickling done"

	def test(self, sentences):
		infered_sentences = []
		l = 0
		for s in sentences:
			l+=1
			word_tag_pairs = self.st.tag(s.words)
			tags = [i for i,j in word_tag_pairs]
			infered_sentences += [sentence.Sentence( s.words, tags )]
			print l

		print "sentences converted"
		for s in infered_sentences:
			trees = s.get_trees()
			i = 0
			no_construction = False
			while ( len(trees) > 0 ):
				if i == len(trees) - 1:
					if no_construction == True:
						break;
					# if we reach the end start from the beginning
					no_construction = True
					i = 0
				else:					
					# extract features
					extracted_features = self.extract_features(trees, i)

					# estimate the action to be taken for i, i+ 1 target  nodes
					y = self.estimate_action(trees, i, extracted_features)
					print y
					# execute the action and modify the trees
					if y!= SHIFT:
						trees = self.take_action(trees, i ,y)
						no_construction = False
					else:
						i += 1
			print trees