from google.appengine.ext import db
from google.appengine.ext import blobstore

	
class Account(db.Model):
  id = db.StringProperty()
  nickname = db.StringProperty()
  email = db.EmailProperty(required=True)
  googleNickname = db.StringProperty()
  name = db.StringProperty()
  level = db.StringProperty()
  status = db.StringProperty()
  description = db.TextProperty()
  profilePicBlobKey = db.StringProperty()
  accountSince = db.DateTimeProperty()
  isStudent = db.BooleanProperty()
  isStudentUntil = db.DateTimeProperty()
  showName = db.BooleanProperty()
  showEmail = db.BooleanProperty()
  authType = db.StringProperty()



class ShopItem(db.Model):
  title = db.StringProperty()
  description = db.TextProperty()
  profilePicBlobKey = db.StringProperty()
  picBlobKeys = db.StringListProperty()
  videoBlobKeys = db.StringListProperty()
  markedPrice = db.IntegerProperty()
  discountPrice = db.IntegerProperty()
  quantity = db.IntegerProperty()
  status = db.StringProperty() # active, inactive
  privacy = db.StringProperty() # Public(all), Custom(select viewer)
  creationDate = db.DateTimeProperty()
  expiryDate = db.DateTimeProperty()
  expireIn = db.IntegerProperty()
  paymentMethod = db.StringProperty()
  owner = db.StringProperty()
  viewCount = db.IntegerProperty()


class Conversation(db.Model):
  title = db.StringProperty(required=True)
  shopItemId = db.StringProperty()
  shopItemPrice = db.IntegerProperty()
  shopItemTitle = db.StringProperty()
  partnerConversationId = db.StringProperty() # NEW
  recordDate = db.DateTimeProperty(required=True,auto_now_add=True)

class ConversationAssignment(db.Model):
  conversation = db.ReferenceProperty(Conversation, collection_name='conversationAssignment')
  ownerAccount = db.ReferenceProperty(Account, collection_name='accountConversationAssignment')
  lastModifiedDate = db.DateTimeProperty(auto_now=True)

class Message(db.Model):
  sender = db.StringProperty(required=True)
  senderApplicationId = db.StringProperty() # NEW
  senderId = db.StringProperty() # NEW
  recipient = db.StringProperty(required=True)
  content = db.TextProperty(required=True)
  owner = db.StringProperty(required=True) # who can see this message
  isRead = db.BooleanProperty()
  parentConversation = db.ReferenceProperty(Conversation, collection_name='messages')
  date = db.DateTimeProperty(required=True,auto_now_add=True)



class WishList(db.Model):
  nickname = db.StringProperty()
  shopItemId = db.StringProperty()



class EventLog(db.Model):
  actor = db.StringProperty(required=True)
  actionType = db.StringProperty(required=True)
  target = db.StringProperty()
  content = db.StringProperty()
  date = db.DateTimeProperty(required=True,auto_now_add=True)


class KeywordRepo(db.Model):
  shopItemId = db.StringProperty(required=True)
  keyword = db.StringProperty(required=True)
  weight = db.IntegerProperty(required=True)


class Transaction(db.Model):
  actor = db.StringProperty(required=True)
  owner = db.StringProperty(required=True)
  status = db.StringProperty()
  itemId = db.StringProperty(required=True)
  quantity = db.IntegerProperty(required=True)
  recordDate = db.DateTimeProperty(required=True,auto_now_add=True)
  endDate = db.DateTimeProperty()
  itemTitle = db.StringProperty()
  itemPrice = db.IntegerProperty()


class StudentAccountVerification(db.Model):
  account = db.StringProperty(required=True)
  email = db.StringProperty(required=True)
  date = db.DateTimeProperty(required=True,auto_now_add=True)


# with memcache
class ApplicationSettings(db.Model):
  type = db.StringProperty(required=True)
  name = db.StringProperty()
  value = db.StringProperty(required=True)
  remarks = db.TextProperty()

#
class ApplicationApiSettings(db.Model):
  domain = db.StringProperty(required=True)
  token = db.StringProperty(required=True)
  apiType = db.StringProperty(required=True)
  remarks = db.TextProperty()


# not implemented yet
class Rating(db.Model):
  rater = db.StringProperty() # the user who wrote the comment
  shopItemId = db.StringProperty()
  rating = db.IntegerProperty()
  comment = db.StringProperty()






