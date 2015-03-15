# -*- coding: utf-8 -*-

import logging

#------- Import from Google ---------
#
from google.appengine.api import users
from google.appengine.ext import db
#
#------------------------------------


#------- Custom Import ---------
#
from commonFunction import createEventLog
from commonFunction import findAccount
from commonFunction import getTokenList
#
#------------------------------------

#------- Datastore Schema -----------
#
import schema
#
#------------------------------------



def AccessControlForMessage(func):
  def handler(self, *paths):
    _requestField = 'conversationId'
    if self.request.get( _requestField , None) is not None:
      account = findAccount()
      
      conversation = schema.Conversation.get_by_id(int(self.request.get( _requestField )))
      if conversation is None:
        logging.info("Account nickname = " + account.nickname + " attempted to access non-existing conversation (id = " + self.request.get( _requestField ) + ") ")
        self.redirect('/error?type=message')
        return
      
      if schema.ConversationAssignment.gql("WHERE conversation = :1 AND ownerAccount = :2", conversation, account).count() == 1:
        return func(self, *paths)
      else:
        logging.info("Access denied for conversationId = " + self.request.get( _requestField ) + " by account nickname = " + account.nickname )
        createEventLog(account.nickname, 'MESSAGE_ACCESS_DENIED', _requestField + ' = ' + self.request.get( _requestField ), self.request.uri)
        self.redirect('/error?type=message')
        return
    else:
      self.redirect('/')
      return
    
  return handler


def AccessControlForShopItem(func):
  def handler(self, *paths):
    _requestField = 'itemId'
    if self.request.get( _requestField , None) is not None:
      account = findAccount()
      
      shopItem = schema.ShopItem.get_by_id(int(self.request.get( _requestField )))
      
      if shopItem is None:
        self.redirect('/error/404?itemId='+self.request.get( _requestField ))
      elif shopItem is not None and shopItem.owner == account.nickname:
        return func(self, *paths)
      else:
        logging.info("User '"+ account.nickname + "' tries to access an shopItem, id = " + \
          self.request.get( _requestField ) + ", which is not belong to this user.")
        
        createEventLog(account.nickname, 'SHOPITEM_ACCESS_DENIED', _requestField+' = '+self.request.get( _requestField ), self.request.uri)
        self.redirect('/error?type=item')
    else:
      self.redirect('/')
      return

  return handler


def AccessControlForTransaction(func):
  def handler(self, *paths):
    _requestField = 'transactionId'
    if self.request.get( _requestField , None) is not None:
      account = findAccount()
      
      transaction = schema.Transaction.get_by_id(int(self.request.get( _requestField )))
      
      if transaction is None:
        self.redirect('/error/404?transactionId='+self.request.get( _requestField ))
      elif transaction is not None and transaction.owner == account.nickname:
        return func(self, *paths)
      elif transaction is not None and transaction.actor == account.nickname:
        return func(self, *paths)
      else:
        logging.info("User '"+ account.nickname + "' tries to access a transaction, id = " + \
          self.request.get( _requestField ) + ", which is not belong to this user.")
        
        createEventLog(account.nickname, 'TRNASACTION_ACCESS_DENIED', _requestField+' = '+self.request.get( _requestField ), self.request.uri)
        self.redirect('/error?type=transaction')
    else:
      self.redirect('/')
      return

  return handler
#

def AdminOnly(func):
  def handler(self, *paths):
    user = users.get_current_user()
    if users.is_current_user_admin():
      return func(self, *paths)
    elif db.GqlQuery("SELECT nickname FROM Account WHERE level = 'admin' and id = :1", user.user_id()).count() == 1:
      return func(self, *paths)
    else:
      self.redirect('/')
    return

  return handler
#


def UserNicknameRequired(func):
  def handler(self, *paths):
    user = users.get_current_user()
    if db.GqlQuery("SELECT nickname FROM Account WHERE googleNickname = :1", user.nickname()).count() == 1:
      account = findAccount()
      if account.status == 'Suspend':
        self.redirect('/error/suspend')
      if account.status == 'Deleted':
        self.redirect('/error/deleted')
      return func(self, *paths)
    else:
      self.redirect('/user/settings/nickname')
    return
  return handler


def AuthRequired(func):
  def handler(self, *paths):
    # check if the request includes auth token
    # the token should be a valid one
    
    token = self.request.get("auth_token" , None)
    
    # if token is missing, return error
    if token is None:
      return self.redirect('/error/api')
      #pass
    
    # if token is invalid, return error
    if token not in getTokenList():
      return self.redirect('/error/api')
      #pass
    
    # correct token.
    return func(self, *paths)
  
  return handler

