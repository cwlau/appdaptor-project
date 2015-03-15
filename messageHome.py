
import logging
import re
import os
import urllib
import webapp2

#---------------- Import from Google ------------------
#
from google.appengine.api import users, images
from google.appengine.ext import db
from google.appengine.ext.webapp import template
#
#------------------------------------------------------

#----------------- Custom Classes & -------------------
#----------------- Datastore Schema -------------------
#
from decorator import AccessControlForMessage
from decorator import UserNicknameRequired
from commonFunction import createEventLog
from commonFunction import dateFromNow
from commonFunction import oneDayOrDate
from commonFunction import getCommonUiParams
from commonFunction import findAccount
from commonFunction import findAccountByNickname
from commonFunction import returnJsonResult
from commonFunction import retrieveApplicationSettings
from schema import WishList
import schema

#
#------------------------------------------------------



class MessageHomeHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/message.html")
    self.response.out.write(template.render(path, getCommonUiParams(self, retrieveApplicationSettings('env', 'conversation_group_size'))))
#

class MessageCreateHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('/')
  
  @UserNicknameRequired
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    
    # TODO run in transaction
    
    account = findAccount()
    if self.request.get('recipient', None) is None:
      returnJsonResult(self, 'false', 'Recipient cannot be blank')
      return
    if self.request.get('title', None) is None:
      returnJsonResult(self, 'false', 'Title cannot be blank')
      return
    if self.request.get('content', None) is None:
      returnJsonResult(self, 'false', 'Content cannot be blank')
      return
    if account is None:
      returnJsonResult(self, 'false', 'Login Required')
      return
    
    shopItemId = None
    shopItemPrice = None
    shopItemTitle = None
    if self.request.get('itemId', '0') != '0':
      shopItemId = self.request.get('itemId')
      
      item = schema.ShopItem.get_by_id(int(shopItemId))
      if item is None:
        returnJsonResult(self, 'false', 'invalid itemId')
        return
      
      shopItemPrice = item.markedPrice
      shopItemTitle = item.title
    
    recipient = str(self.request.get('recipient'))
    recipients = re.sub(' ', '', str(urllib.unquote(recipient))).split(',')
    
    _max_recipient_count = int(retrieveApplicationSettings('env', 'conversation_group_size'))
    if len(recipients) > _max_recipient_count:
      returnJsonResult(self, 'false', 'Exceed maximum number of recipients.\\nCurrent limit = ' + str(_max_recipient_count))
      return
    
    errorList = []
    for recipient in recipients:
      if account.nickname == recipient:
        returnJsonResult(self, 'false', 'You cannot send messages to yourself')
        return
        
      recipientAccount = findAccountByNickname(recipient)
      if recipientAccount is None:
        errorList += (recipient,)
        
    recipients += ( account.nickname, )
    
    if len(errorList) != 0:
      returnJsonResult(self, 'false', 'User '+','.join(errorList)+' does not exist')
      return
    
    
    # Create New Conversation
    newConversation = schema.Conversation(
      title = self.request.get('title'),
      shopItemId = shopItemId,
      shopItemPrice = shopItemPrice,
      shopItemTitle = shopItemTitle
    )
    newConversation.put()
    
    
    for recipient in recipients:
      
      recipientAccount = findAccountByNickname(recipient)
      
      if recipient == account.nickname:
        messageIsRead = True
      else:
        messageIsRead = False
      
      # Create Message in conversation
      newMessage = schema.Message(
        sender = account.nickname,
        recipient = self.request.get('recipient'),
        content = self.request.get('content'),
        owner = recipient,
        isRead = messageIsRead,
        parentConversation = newConversation
      )
      newMessage.put()
      
      # Assign Conversation to each sender/ recipient
      assignment = schema.ConversationAssignment(
        conversation = newConversation,
        ownerAccount = recipientAccount
      )
      assignment.put()
    
    createEventLog(account.nickname, 'MESSAGE_CREATE', 'conversationId = '+str(newConversation.key().id()), 'recipient(s) = '+(','.join(recipients)) )
    returnJsonResult(self, 'true')


#
# any message with ConversationAssignment.owner = account.nickname
class ListInboxHandler(webapp2.RequestHandler):
  def get(self):
    self.post() #TODO Debug only
    return
    self.redirect('/')
  
  @UserNicknameRequired
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    path = os.path.join(os.path.dirname(__file__), "template/messageTitleList.json")
    
    account = findAccount()
    conversationQuery = schema.ConversationAssignment.all().filter("ownerAccount = ", account).order("-lastModifiedDate")
    
    
    result_length = 999999
    conversations = conversationQuery.fetch(result_length)
    result_length = min(result_length, len(conversations))
    
    conversationList = []
    index = 0
    
    #inbox
    for i in conversations:
      
      if result_length-1 == index:
        noComma = 'True'
      else:
        index = index + 1
        noComma = 'False'
      
      isRead = (schema.Message.gql("WHERE parentConversation = :1 and isRead = :2 and owner = :3", i.conversation, False, account.nickname).count() == 0)
      messageCount = schema.Message.gql("WHERE parentConversation = :1 and owner = :2", i.conversation, account.nickname).count()
      latestMessage = schema.Message.gql("WHERE parentConversation = :1 ORDER BY date DESC", i.conversation).fetch(1)
      for m in latestMessage:
      #messageDate = oneDayOrDate(m.date)
      #date_fromnow = dateFromNow(m.date)
      #exactDate = m.date
        latestSender = m.sender
      
      messageDate = oneDayOrDate(i.lastModifiedDate)
      date_fromnow = dateFromNow(i.lastModifiedDate)
      exactDate = i.lastModifiedDate
      
      conversationInfo = {
        'id': i.conversation.key().id(),
        'sender': latestSender,
        'title': i.conversation.title,
        'messageCount': messageCount,
        'shopItemId': i.conversation.shopItemId,
        'shopItemPrice': i.conversation.shopItemPrice,
        'datetime': messageDate,
        'exactDate': exactDate,
        'date_fromnow': date_fromnow,
        'isRead': isRead,
        'noComma': noComma
      }
      
      conversationList.append(conversationInfo)
    
    if len(conversationList)==0:
      conversationList.append({
        'endOfList': 'True',
        'noComma': 'True'
      })
    
    resultList = {
      'conversationList': conversationList,
    }
    self.response.out.write(template.render(path, resultList))
    return
    


# any message with ConversationAssignment.owner = account.nickname and Message.isRead = False
class ListUnreadHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('/')
  
  @UserNicknameRequired
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    path = os.path.join(os.path.dirname(__file__), "template/messageTitleList.json")
    
    account = findAccount()
    conversationQuery = schema.ConversationAssignment.all().filter("ownerAccount = ", account).order("-lastModifiedDate")
    
    
    result_length = 999999
    conversations = conversationQuery.fetch(result_length)
    result_length = min(result_length, len(conversations))
    
    conversationList = []
    index = 0
    
    #unread
    for i in conversations:
      # temporary solution: get all then filter unread messages
      # TODO performance tuning 
      isRead = (schema.Message.gql("WHERE parentConversation = :1 and isRead = :2 and owner = :3", i.conversation, False, account.nickname).count() == 0)
      
      if result_length-1 == index:
        noComma = 'True'
      else:
        index = index + 1
        noComma = 'False'
      
      if isRead == True:
        if noComma == 'False':
          continue # not the last item of list
        else:
          conversationInfo = {
            'endOfList': 'True',
            'noComma': noComma
          }
          conversationList.append(conversationInfo)
          continue # the last item of list
      
      
      isRead = (schema.Message.gql("WHERE parentConversation = :1 and isRead = :2 and owner = :3", i.conversation, False, account.nickname).count() == 0)
      messageCount = schema.Message.gql("WHERE parentConversation = :1 and owner = :2", i.conversation, account.nickname).count()
      latestMessage = schema.Message.gql("WHERE parentConversation = :1 ORDER BY date DESC", i.conversation).fetch(1)
      for m in latestMessage:
        latestSender = m.sender
      
      messageDate = oneDayOrDate(i.lastModifiedDate)
      date_fromnow = dateFromNow(i.lastModifiedDate)
      exactDate = i.lastModifiedDate
      
      conversationInfo = {
        'id': i.conversation.key().id(),
        'sender': latestSender,
        'title': i.conversation.title,
        'messageCount': messageCount,
        'shopItemId': i.conversation.shopItemId,
        'shopItemPrice': i.conversation.shopItemPrice,
        'datetime': messageDate,
        'exactDate': exactDate,
        'date_fromnow': date_fromnow,
        'isRead': isRead,
        'noComma': noComma
      }
      
      conversationList.append(conversationInfo)
    
    if len(conversationList)==0:
      conversationList.append({
        'endOfList': 'True',
        'noComma': 'True'
      })
    
    resultList = {
      'conversationList': conversationList,
    }
    self.response.out.write(template.render(path, resultList))
    return


# any message with ConversationAssignment.owner = account.nickname and Message.sender = account.nickname
class ListSentHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('/')
  
  @UserNicknameRequired
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    path = os.path.join(os.path.dirname(__file__), "template/messageTitleList.json")
    
    account = findAccount()
    conversationQuery = schema.ConversationAssignment.all().filter("ownerAccount = ", account).order("-lastModifiedDate")
    
    
    result_length = 999999
    conversations = conversationQuery.fetch(result_length)
    result_length = min(result_length, len(conversations))
    
    conversationList = []
    index = 0
    
    #sent
    for i in conversations:
      # temporary solution: get all then filter unread messages
      # TODO performance tuning 
      isSent = (schema.Message.gql("WHERE parentConversation = :1 and owner = :2 and sender = :3", i.conversation, account.nickname, account.nickname).count() > 0)
      
      if result_length-1 == index:
        noComma = 'True'
      else:
        index = index + 1
        noComma = 'False'
      
      if isSent == False:
        if noComma == 'False':
          continue # not the last item of list
        else:
          conversationInfo = {
            'endOfList': 'True',
            'noComma': noComma
          }
          conversationList.append(conversationInfo)
          continue # the last item of list
      
      isRead = (schema.Message.gql("WHERE parentConversation = :1 and isRead = :2 and owner = :3", i.conversation, False, account.nickname).count() == 0)
      messageCount = schema.Message.gql("WHERE parentConversation = :1 and owner = :2", i.conversation, account.nickname).count()
      latestMessage = schema.Message.gql("WHERE parentConversation = :1 and owner = :2 ORDER BY date DESC", i.conversation, account.nickname).fetch(1)
      if latestMessage is None:
        returnJsonResult(self, 'false', 'Error retrieving values.')
        return
        
      for m in latestMessage:
        latestSender = m.sender
      
      messageDate = oneDayOrDate(i.lastModifiedDate)
      date_fromnow = dateFromNow(i.lastModifiedDate)
      exactDate = i.lastModifiedDate
      
      conversationInfo = {
        'id': i.conversation.key().id(),
        'sender': latestSender,
        'title': i.conversation.title,
        'messageCount': messageCount,
        'shopItemId': i.conversation.shopItemId,
        'shopItemPrice': i.conversation.shopItemPrice,
        'datetime': messageDate,
        'exactDate': exactDate,
        'date_fromnow': date_fromnow,
        'isRead': isRead,
        'noComma': noComma
      }
      
      conversationList.append(conversationInfo)
    
    if len(conversationList)==0:
      conversationList.append({
        'endOfList': 'True',
        'noComma': 'True'
      })
    
    resultList = {
      'conversationList': conversationList,
    }
    self.response.out.write(template.render(path, resultList))
    return
#







class MessageReplyHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('/')
  
  @UserNicknameRequired
  @AccessControlForMessage
  def post(self):
    
    # TODO run in transaction
    
    loginAccount = findAccount()
    conversation = schema.Conversation.get_by_id(int(self.request.get( 'conversationId' )))
    
    conversationAssignmentQuery = schema.ConversationAssignment.all().filter("conversation = ", conversation)
    conversationAssignment = conversationAssignmentQuery.fetch(10)
    
    recipientList = []
    for assignment in conversationAssignment:
      currentAccount = assignment.ownerAccount
      recipientList.append(currentAccount.nickname)
      # update ConversationAssignment lastModifiedDate
      assignment.put()
      
    for assignment in conversationAssignment:
      currentAccount = assignment.ownerAccount
    
      if loginAccount.nickname == currentAccount.nickname:
        messageIsRead = True
      else:
        messageIsRead = False
      
      # Create Message in conversation
      newMessage = schema.Message(
        sender = loginAccount.nickname,
        recipient = ','.join(recipientList),
        content = self.request.get('content'),
        owner = currentAccount.nickname,
        isRead = messageIsRead,
        parentConversation = conversation
      )
      newMessage.put()
    
    createEventLog(loginAccount.nickname, 'MESSAGE_REPLY', 'conversationId = '+self.request.get( 'conversationId' ), 'recipient(s) = '+(','.join(recipientList)) )
    
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    returnJsonResult(self, 'true')
    return
#





class MessageThreadHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('/')
  
  @UserNicknameRequired
  @AccessControlForMessage
  def post(self):
    
    account = findAccount()
    
    conversation = schema.Conversation.get_by_id(int(self.request.get( 'conversationId' )))
    messageQuery = schema.Message.all().filter("parentConversation = ", conversation).filter("owner = ", account.nickname).order("date")
    
    result_length = 1000
    messages = messageQuery.fetch(result_length)
    result_length = min(result_length, len(messages))
    
    conversationList = []
    index = 0
    
    messageList = []
    for message in messages:
      if message.isRead == False:
        message.isRead = True
        message.put()
      
      senderAccount = findAccountByNickname(message.sender)
      
      if result_length-1 == index:
        noComma = 'True'
      else:
        index = index + 1
        noComma = 'False'
      
      if senderAccount is not None and senderAccount.profilePicBlobKey is not None and senderAccount.profilePicBlobKey != '':
        senderAccountImageLinkUrl = images.get_serving_url(senderAccount.profilePicBlobKey, size=None, crop=False, secure_url=True)
        senderAccountImageUrl = senderAccountImageLinkUrl + '=s108-c'
      else:
        senderAccountImageLinkUrl = ''
        senderAccountImageUrl = '/image/user.jpg'
      
      
      messageInfo = {
        'sender': message.sender,
        'senderImageUrl': senderAccountImageUrl,
        'recipient': message.recipient,
        'content': message.content,
        'isRead': message.isRead,
        'datetime': oneDayOrDate(message.date),
        'exactDate': message.date,
        'date_fromnow': dateFromNow(message.date),
        'noComma': noComma
      }
      
      messageList.append(messageInfo)
    
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    path = os.path.join(os.path.dirname(__file__), "template/messageContentList.json")
    
    resultList = {
      'messageList': messageList
    }
    
    self.response.out.write(template.render(path, resultList))
#



#
class ConversationViewHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  def get(self, conversationId):
    if not conversationId.isdigit() or int(conversationId) <1:
      self.response.out.write("Bad request")
      return
      
    account = findAccount()
    
    conversation = schema.Conversation.get_by_id(int(conversationId))
    if conversation is None:
      self.response.out.write("Conversation not found.")
      return
    
    if schema.ConversationAssignment.gql("WHERE conversation = :1 AND ownerAccount = :2", conversation, account).count() != 1:
      createEventLog(account.nickname, 'MESSAGE_ACCESS_DENIED', 'conversationId = '+conversationId, self.request.uri)
      self.redirect('/error?type=message')
      return
    
    recipientQuery = schema.ConversationAssignment.all().filter("conversation = ", conversation)
    recipientList = recipientQuery.fetch(100)
    
    recipientsInfo = []
    for assi in recipientList:
      accountImageUrl = ''
      if assi.ownerAccount.profilePicBlobKey is not None and assi.ownerAccount.profilePicBlobKey != '':
        accountImageUrl = images.get_serving_url(assi.ownerAccount.profilePicBlobKey, size=None, crop=False, secure_url=True) + '=s24-c'
      else:
        accountImageUrl = '/image/user.jpg'
      
      recipientsInfo.append({
        'nickname': assi.ownerAccount.nickname,
        'image': accountImageUrl
      })
    
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/messageThread.html")
    
    
    shopItemId = 0
    shopItemTitle = ''
    shopItemPrice = ''
    shopItemImageUrl = '/image/noimage.png'
    if conversation.shopItemId is not None:
      shopItemId = conversation.shopItemId
      shopItemTitle = conversation.shopItemTitle
      shopItemPrice = conversation.shopItemPrice/100.0
      item = schema.ShopItem.get_by_id(int(conversation.shopItemId))
      if item.profilePicBlobKey is not None and item.profilePicBlobKey != '':
        shopItemImageUrl = images.get_serving_url(item.profilePicBlobKey, size=None, crop=False, secure_url=True)+'=s108-c'
    
    
    conversationInfo = {
      'id': conversationId,
      'title': conversation.title,
      'recipientsInfo': recipientsInfo,
      'itemId': shopItemId,
      'itemTitle': shopItemTitle,
      'itemImageUrl': shopItemImageUrl,
      'itemPriceInFloat': shopItemPrice,
      'conversationBeginDate': conversation.recordDate,
    }
    
    self.response.out.write(template.render(path, getCommonUiParams(self, conversationInfo)))
    return
#


class UnreadCountHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  def post(self):
    account = findAccount()
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    unreadCount = db.GqlQuery("SELECT __key__ FROM Message WHERE owner = :1 AND isRead = :2", account.nickname, False).count()
    returnJsonResult(self, 'true', unreadCount)
    return
#





app = webapp2.WSGIApplication([
  ('/message/', MessageHomeHandler),
  ('/message/create', MessageCreateHandler),
  ('/message/reply', MessageReplyHandler),
  ('/message/inbox', ListInboxHandler),
  ('/message/unread', ListUnreadHandler),
  ('/message/unreadCount', UnreadCountHandler),
  ('/message/sent', ListSentHandler),
  ('/message/thread', MessageThreadHandler),
  ('/message/([^/]+)', ConversationViewHandler)
], debug=True)


