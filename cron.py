

import datetime
import logging
import os
import webapp2

#---------------- Import from Google ------------------
#
from google.appengine.api import users, mail, xmpp
#
#------------------------------------------------------

#----------------- Custom Classes & -------------------
#----------------- Datastore Schema -------------------
#
from commonFunction import createEventLog
from commonFunction import findAccountByNickname
from commonFunction import retrieveApplicationSettings
import schema

#
#------------------------------------------------------


class CheckExpiredShopItemHandler(webapp2.RequestHandler):
  def get(self):
    
    jobEnabled = retrieveApplicationSettings('cron', 'cron_item_expiryDateChecker')
    if jobEnabled != '1':
      logging.info("cron job disabled by admin. skipped checking item expiry date.")
      self.response.out.write("cron job skipped")
      return
    
    logging.info("cron job enabled. continue checking item expiry date.")
    
    item_expire_alert_daysBefore = retrieveApplicationSettings('env', 'item_expire_alert_daysBefore')
    
    # get all shop item , one-by-one check expiry date
    # if date is passed -> mark as expired
    
    # if deadline is close, send reminder
    
    shopItemQuery = schema.ShopItem.all().filter("status = ", 'Active')
    shopItems = shopItemQuery.fetch(999999)
    
    
    for item in shopItems:
      if item.expiryDate is not None:
        if item.expiryDate < datetime.datetime.today():
          account = findAccountByNickname(item.owner)
          item.status = 'Expired'
          item.put()
          logging.info('item "' + item.title + '", (ID = ' + \
                str(item.key().id())+') is expired.')
          result = xmpp.send_message(
            account.email,
            'This is a reminder from Demo Shop. Your item "' + item.title + '", (ID = ' + \
                str(item.key().id())+') is expired. This item will not be visible by others. ' \
                'If you would like to continue to offer this item, please create a new item.'
            
          )
          createEventLog('robot', 'EXPIRE_ITEM', 'itemId = '+str(item.key().id()), '')
          logging.info('Expire notification is sent to owner "' + item.owner + '", (ID = ' + \
                str(account.email) +') by XMPP message.')
        elif datetime.datetime.today() + datetime.timedelta(days=item_expire_alert_daysBefore) < item.expiryDate < datetime.datetime.today() + datetime.timedelta(days=4):
          # notify owner for item expires in [item_expire_alert_daysBefore] days (default = 3)
          account = findAccountByNickname(item.owner)
          result = xmpp.send_message(
            account.email,
            'This is a reminder from Demo Shop. Your item "' + item.title + '", (ID = ' + \
                str(item.key().id())+') will expire in ' + item_expire_alert_daysBefore + ' days.' \
            
          )
          createEventLog('robot', 'EXPIRE_ITEM_REMINDER', 'itemId = '+str(item.key().id()), '')
          logging.info('Expire reminder is sent to owner "' + item.owner + '", (ID = ' + \
                str(account.email) +') by XMPP message.')
    self.response.out.write("DONE")
#

class CheckExpiredStudentAccountHandler(webapp2.RequestHandler):
  def get(self):
    
    jobEnabled = retrieveApplicationSettings('cron', 'cron_account_expiryDateChecker')
    if jobEnabled != '1':
      logging.info("cron job disabled by admin. skipped checking student identity expiry date.")
      self.response.out.write("cron job skipped")
      return
    
    logging.info("cron job enabled. continue checking student identity expiry date.")
    
    # get all student account , one-by-one check expiry date
    
    studentAccountQuery = schema.Account.all().filter("isStudent = ", True)
    students = studentAccountQuery.fetch(999999)
    
    # TODO batch update
    for student in students:
      if student.isStudentUntil < datetime.datetime.today():
        student.isStudentUntil = None
        student.isStudent = False
        student.put()
        logging.info("Student account '" + student.nickname + "' expires")
        createEventLog('robot', 'STUDENT_ACCOUNT_EXPIRE', 'account = ' + student.nickname, '')
      
    self.response.out.write("DONE")
#



app = webapp2.WSGIApplication([
  ('/cron/checkExpiredShopItem', CheckExpiredShopItemHandler),
  ('/cron/checkExpiredStudentAccount', CheckExpiredStudentAccountHandler)
], debug=True)


