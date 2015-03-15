# -*- coding: utf-8 -*-
#!/usr/bin/env python
#--high_replication --clear_datastore

import datetime
import logging
import os
import re
import webapp2

#------- Import from Google ---------
#
from google.appengine.api import mail
from google.appengine.ext import db
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
#
#------------------------------------


#----------------- Custom Classes & -------------------
#----------------- Datastore Schema -------------------
from commonFunction import createEventLog
from commonFunction import findAccount
from commonFunction import findAccountByNickname
import schema
#
#------------------------------------------------------

class VerifyStudentAccountHandler(InboundMailHandler):
  def receive(self, mail_message):
    
    _application_id = os.environ.get('APPLICATION_ID', 'hardcode-appdaptor')
    _application_id = re.sub('s~', '', _application_id)
    
    _signature = "Demo Shop<br/>The Appdaptor Team"
    
    logging.info("From: " + mail_message.sender)
    logging.info("Subject: \"" + mail_message.subject + "\"")
    
    
    # check subject, find the account
    subject = mail_message.subject
    accountNickname = re.sub('VERIFY STUDENT ACCOUNT:', '', subject)
    accountNickname = accountNickname.strip(' \t\n\r') # remove all space characters
    logging.info( "accountNickname = \"" + accountNickname + "\"")
    
    
    # check is sender email a valid student email account
    _sender_email = mail_message.sender.split("<")[-1].split(">")[0]
    
    #if not(re.match(r"[^@]+@[^@]+\.edu+[^@]+", _sender_email)):
    #  html_bodies = mail_message.bodies('text/html')
    #
    #  for content_type, body in html_bodies:
    #  
    #    newMessage = mail.EmailMessage(sender = "Demo Shop Support <noreply@" +_application_id+ ".appspotmail.com>",
    #                                  subject = "Cannot Verify Account: " + accountNickname)
    #    newMessage.to = mail_message.sender
    #    newMessage.html = """
    #    Dear %s,<br/><br/>
    #    Thank you for trying Demo Shop service.<br/><br/>
    #    
    #    However, to prevent abuse of our service, you will need to verify your account (%s)
    #    with your school email, which ends with "@*.edu(.*)" in the email domail.
    #    Please verify your account again with the your school email.<br/><br/>
    #    
    #    Thanks,<br/><br/>%s<br/><br/>
    #    (This is a system generated message. Please do not reply this email.)
    #    <br/><br/>
    #    <div style="font-size:0.9em;color:#666;">
    #    Quoted text:<br/>%s
    #    </div>
    #    """% (mail_message.sender, accountNickname, _signature, body.decode())
    #    
    #    newMessage.send()
    #    
    #  logging.info("Cannot verify account. Sender email (" + mail_message.sender + ") is not from .edu domain.")
    #  createEventLog(accountNickname, 'STUDENT_ACCOUNT_VERIFY_FAILED', 'sender = ' + mail_message.sender , 'Sender email is not from .edu domain' )
    #  return
      
    
    
    
    account = findAccountByNickname(accountNickname)
    if account is None:
      
      html_bodies = mail_message.bodies('text/html')

      for content_type, body in html_bodies:
      
        newMessage = mail.EmailMessage(sender = "Demo Shop Support <noreply@" +_application_id+ ".appspotmail.com>",
                                      subject = "Cannot Verify Account: " + accountNickname)
        newMessage.to = mail_message.sender
        newMessage.html = """
        Dear %s,<br/><br/>
        Thank you for trying Demo Shop service.<br/><br/>
        However, the account name "%s" was not found in our server. Please check again with the your username.<br/><br/>
        
        Thanks,<br/><br/>%s<br/><br/>
        (This is a system generated message. Please do not reply this email.)
        <br/><br/>
        <div style="font-size:0.9em;color:#666;">
        Quoted text:<br/>%s
        </div>
        """% (mail_message.sender, accountNickname, _signature, body.decode())
        
        newMessage.send()
      
      logging.info("Cannot find account with nickname = " + accountNickname)
      logging.info(mail_message.sender + " sent an email with subject: " + mail_message.subject+", cannot verify student account")
      return
    
    elif db.GqlQuery("SELECT * FROM StudentAccountVerification WHERE email = :1 and account != :2 ", mail_message.sender, accountNickname).count() > 0:
      # 
      logging.info("Duplicate student email: Email sender = " + mail_message.sender + ", Account = " + accountNickname + ". Account not verified")
      
      newMessage = mail.EmailMessage(sender = "Demo Shop Support <noreply@" +_application_id+ ".appspotmail.com>",
                                    subject = "Cannot Verify Account: " + accountNickname)
      newMessage.to = mail_message.sender
      newMessage.html = """
      Dear %s,<br/><br/>
      Thank you for trying Demo Shop service.<br/><br/>
      
      Recently you attempted to verify account "%s" as student. However, the action failed because your email address was already used to verify another account. Each email address can only be used to verify one account.<br/><br/>
      
      Thanks,<br/><br/>%s<br/><br/>
      (This is a system generated message. Please do not reply this email.)
      <br/>
      """% (mail_message.sender, accountNickname, _signature)
      createEventLog(accountNickname, 'STUDENT_ACC_VERIFY_FAILED', 'sender = ' + mail_message.sender , 'Duplicate student email sender' )
    
    else:
      account.isStudent = True
      account.isStudentUntil = datetime.datetime.now() + datetime.timedelta(days=365)
      account.put()
      
      # send email to user about their student account has been verified
      newMessage = mail.EmailMessage(sender = "Demo Shop Support <noreply@" + _application_id + ".appspotmail.com>",
                                    subject = "Your Account (" + accountNickname + ") has been verified as Student Account")
      newMessage.to = mail_message.sender
      newMessage.html = """
      Dear %s,<br/><br/>
      Contragulations! Your student account ("%s") has been verified!<br/>
      The student identity will be valid for 1 year upon verification.<br/><br/>
      Thank you for trying Demo Shop service. Enjoy shopping!<br/><br/>
      
      %s<br/><br/>
      (This is a system generated message. Please do not reply this email.)
      <br/>
      """% (mail_message.sender, accountNickname, _signature)
      newMessage.send()
      
      if db.GqlQuery("SELECT * FROM StudentAccountVerification WHERE email = :1 and account = :2 ", mail_message.sender, accountNickname).count() == 0:
        verification = schema.StudentAccountVerification(
          account = accountNickname,
          email = mail_message.sender
        )
        verification.put()
        logging.info("Saved StudentAccountVerification record")
      
      logging.info("Set account.isStudent = True for account " + accountNickname)
      createEventLog(accountNickname, 'STUDENT_ACCOUNT_VERIFY', 'sender = ' + mail_message.sender , '' )
      return



verifyStudent = webapp2.WSGIApplication([VerifyStudentAccountHandler.mapping()], debug=True)


class GeneralEmailHandler(InboundMailHandler):
  def receive(self, mail_message):
    
    _application_id = os.environ.get('APPLICATION_ID', 'hardcode-appdaptor')
    _application_id = re.sub('s~', '', _application_id)
    
    logging.info("From: " + mail_message.sender)
    logging.info("Subject: \"" + mail_message.subject + "\"")
    
    html_bodies = mail_message.bodies('text/html')

    for content_type, body in html_bodies:
      decoded_html = body.decode()
      logging.info("Mail content: " + decoded_html)

      newMessage = mail.EmailMessage(sender="Demo Shop Support <noreply@" + _application_id + ".appspotmail.com>",
                            subject="Mail Delivery Error (" + mail_message.subject + ")")

      newMessage.to = mail_message.sender
      newMessage.html = """
      Hi,<br/><br/>
      The email was not delivered to the recipient. Recipient address (%s) does not exist.
      <br/><br/>
      
      %s<br/><br/>
      (This is a system generated message. Please do not reply this email.)
      <br/><br/>
      <div style="font-size:0.9em;color:#666;">
      Quoted text:<br/>%s
      </div>
      """ % (mail_message.to, _signature, decoded_html)

      newMessage.send()


general = webapp2.WSGIApplication([GeneralEmailHandler.mapping()], debug=True)


