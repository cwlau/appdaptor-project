

page = {

  init: function(){
    // init page here
    
		this.activiateHandlers();
  },

  activiateHandlers: function(){
    
    $("#moduleSearchInput").autocomplete({
      source: function(request, response) {
        $.ajax({
          type: "POST",
          url: "/search/suggest",
          dataType: "json",
          data: {
            value : request.term,
            target : "allItem"
          },
          success: function(data) {
            response(data);
            
          },error: function(data){
            console.log("Error occurred.");
          }
        });
      },
      minLength: 1,
      select: function(event, ui) {
      
      }
    }).live("keyup", function(e){
      if(e.keyCode == 13){
        $(".searchButton").trigger("click");
      }
    });
    
    
    $(".shopItem").live("click", function(){
      if($(this).hasClass("shopItemActive")){
        $(this).removeClass("shopItemActive"); return;
      }
      $(".shopItemActive").removeClass("shopItemActive");
      $(this).addClass("shopItemActive");
    });
    
    
  },

  z:1
};

var messageUtil = {

  init: function(){
		this.activiateHandlers();
  },
  
  formLocked : false,
  sendLocked : false,
  recipientValue: "",
  contentValue: "",
  titleValue: "",

  activiateHandlers: function(){
    $(".composeMessage").live("click", function(){
      if (_LOGGED_IN == ""){alert("Please login to use this function.");return;}
      if (_USERTYPE == ""){alert("Hi visitor, please get a nickname to use this function.");return;}
      if($(this).data("owner")==_MY_ACCOUNT_NICKNAME ){alert("You cannot send message to yourself.");return;}
      
      // Use ajax request to get item title.
      // Prevent security issues in using data- attributes in html element.
      var owner = $(this).data("owner");
      var itemid = $(this).data("itemid");
      if (itemid == undefined){
        messageUtil.createComposeDialog(owner, "", 0);
        return;
      }
      
      $(".loading_msg").show();
      $.ajax({
        type: "POST",
        url:  "/item/findTitle",
        dataType: "json",
        data: {
          itemId: itemid
        },
        success: function(data){
          if(data[0].success == "false"){
            alert( data[0].message );
            $(".loading_msg").hide();
            return;
          }
          
          messageUtil.createComposeDialog(owner, data[0].message, itemid);
          $(".loading_msg").hide();
        },
        error: function(){
          alert(_GENERAL_ERROR);
          $(".loading_msg").hide();
        }
        
      });
    });
    
    $(".createOrder").live("click", function(){
      if (_LOGGED_IN == ""){
        alert("Please login to use this function.");
        return;
      }
      if (_USERTYPE == ""){
        alert("Hi visitor, please get a nickname to use this function.");
        return;
      }
      if($(this).data("owner")==_MY_ACCOUNT_NICKNAME ){return;}
      
      // Use ajax request to get item title.
      // Prevent security issues in using data- attributes in html element.
      var owner = $(this).data("owner");
      var itemid = $(this).data("itemid");
      var price = $(this).data("price");
      
      $(".loading_msg").show();
      $.ajax({
        type: "POST",
        url:  "/item/findTitle",
        dataType: "json",
        data: {
          itemId: itemid
        },
        success: function(data){
          if(data[0].success == "false"){
            alert( data[0].message );
            return;
          }
          
          messageUtil.createOrderDialog(owner, data[0].message, itemid, price);
          messageUtil.formLocked = true;
          $(".loading_msg").hide();
        },
        error: function(){
          alert(_GENERAL_ERROR);
          $(".loading_msg").hide();
        }
        
      });
      
    });
    
    
    $(".messageTitleInput").live("keyup", function(){
      console.log($(this).val() );
      messageUtil.titleValue = $(this).val();
      messageUtil.formLocked = true;
    });
    
    $(".messageRecipientInput").live("keyup", function(){
      messageUtil.recipientValue = $(this).val();
      messageUtil.formLocked = true;
    });
    
    $(".popup-messageContent").live("keyup", function(){
      messageUtil.contentValue = $(this).val();
      messageUtil.formLocked = true;
    });
  },
  
  createComposeDialog: function(recipient, title, itemid){
    messageUtil.formLocked = false;
    messageUtil.recipientValue = "";
    messageUtil.contentValue = "";
    messageUtil.titleValue = "";
    if (itemid==undefined){
      messageUtil.itemIdValue = 0;
    }else{
      messageUtil.itemIdValue = itemid;
    }
    
    messageUtil.createBackground();
    messageUtil.createDialogContent(recipient, title, messageUtil.itemIdValue);
    messageUtil.centerDialog();
    
  },
  
  createBackground: function(){
    var bgDiv = "<div class='popup-backgroundAlpha'></div>";
    $("body").append( bgDiv );
    
    $(".popup-backgroundAlpha").click(function(){
      if(messageUtil.formLocked == false){
        $(this).fadeOut();
        setTimeout("$(this).remove()", 500);
        $(".popup-messageComposer").fadeOut();
        setTimeout("$('.popup-messageComposer').remove()", 500);
      }
    });
  },
  
  createDialogContent: function(recipient, title, itemid){
    var bgDiv = "<div class='popup-messageComposer'><div class='popup-messageComposerContainer'></div></div>";
    $("body").append( bgDiv );
    
    var dialogContent = "";
    dialogContent += "<div class='popupMessageTitle'>Send a message</div><div class='popup-mainArea'>" + messageUtil.createTo(recipient);
    dialogContent += messageUtil.createTitle(title, itemid);
    dialogContent += messageUtil.createTextarea() + "</div>";
    dialogContent += "<div class='popup-bottomControlArea'>" + messageUtil.createBottomButton() + "</div>";
    $(".popup-messageComposerContainer").append( dialogContent );
    
    
    $(".sendMessageButton").click(function(){
      messageUtil.sendMessage();
    });
    
    $(".cancelMessageButton").click(function(){
      
      if (messageUtil.formLocked != false){
        c = confirm("Are you sure to discard the message?");
      }
      
      if (messageUtil.formLocked == false || c == true){
        $(".popup-backgroundAlpha").fadeOut();
        setTimeout("$('.popup-backgroundAlpha').remove()", 500);
        $(".popup-messageComposer").fadeOut();
        setTimeout("$('.popup-messageComposer').remove()", 500);
      }
    });
  },
  
  createTo: function(recipient){
    var inputValueField = "";
    if(recipient != null){
      inputValueField = "<div class='staticValue'>"+ recipient +"</div>";
      messageUtil.recipientValue = recipient;
    } else {
      inputValueField = "<input type='text' class='messageRecipientInput' value='' /><br/><span class='formTips'>Use comma (,) to separate recipients. </span>";
      inputValueField += _MAX_RECIPIENT_MSG;
    }
    var content = "<div class='messageFormField messageTo'><div class='messageAttrDesc'>To:</div><div class='messageAttrInput'>"
        + inputValueField
        + "</div></div>";
    
    return content;
  },
  
  createTitle: function(title, itemid){
    if (title != null && title != ""){
      messageUtil.titleValue = "About item \""+ title +"\"";
      if (itemid != 0){
        messageUtil.titleValue += " (Item ID = "+itemid + ")";
      }
    }
    var inputValueField = "<input type='text' class='messageTitleInput' value='" + messageUtil.titleValue + "' />";
    var content = "<div class='messageFormField messageTitle'><div class='messageAttrDesc'>Title:</div><div class='messageAttrInput'>"
        + inputValueField
        + "</div></div>";
    
    return content;
  },
  
  createTextarea: function(){
    var inputValueField = "<input type='text' value='' />";
    var content = "<div class='messageFormField messageContent'><div class='messageAttrDesc'>Content:</div><div class='messageAttrInput'>"
        + "<textarea class='popup-messageContent'></textarea>"
        + "</div></div>";
    
    return content;
  },
  
  createBottomButton: function(){
    var content = "<div class='messageFormField '><div class='messageAttrDesc'></div><div class='messageAttrInput'>"
        + "<span class='button linkButton sendMessageButton'>Send</span> "
        + "<span class='button linkButton cancelMessageButton'>Cancel</span>"
        + "</div></div>";
    
    return content;
  },
  
  sendMessage: function(){
    // prevent double submission from UI
    if (messageUtil.sendLocked == true) return;
    
    messageUtil.sendLocked = true;
    
    // recipient, title and content cannot be blank.
    if(messageUtil.recipientValue == ""){
      alert("Recipient Field cannot be blank.");
      messageUtil.sendLocked = false;
      return;
    }
    if(messageUtil.titleValue == ""){
      alert("Title Field cannot be blank.");
      messageUtil.sendLocked = false;
      return;
    }
    if(messageUtil.contentValue == ""){
      alert("Content Field cannot be blank.");
      messageUtil.sendLocked = false;
      return;
    }
    
    $(".loading_msg").show();
    var requestUrl = "/message/create";
    var errorCount = 0;
    
    $.ajax({
      type: "POST",
      url:  requestUrl,
      dataType: "json",
      data: {
        recipient: messageUtil.recipientValue,
        title: messageUtil.titleValue,
        content: messageUtil.contentValue,
        itemId: messageUtil.itemIdValue
      },
      success: function(data){
        
        $.each(data, function(i,result){
          if (result['success'] == "false"){
            alert( result['message'] );
            errorCount++;
          }
        });
        
        if (errorCount==0){
          
          // close dialog
          $(".popup-messageComposer").fadeOut();
          setTimeout("$('.popup-messageComposer').remove()", 500);
          
          // show success dialog, auto hiding
          $(".popup-backgroundAlpha").fadeOut();
          setTimeout("$('.popup-backgroundAlpha').remove()", 1500);
          
          composeSuccess();
        }
        
        $(".loading_msg").hide();
        messageUtil.sendLocked = false;
        
        
      },
      error: function(){
        alert(_GENERAL_ERROR);
        $(".loading_msg").hide();
      }
      
    });
    
  },
  
  centerDialog: function(){
    $(".popup-messageComposer").css({
      "top": ($(window).height() - $(".popup-messageComposer").height()) / 2 - 20,
      "left": ($(window).width() - $(".popup-messageComposer").width()) / 2
    })
  },
  
  renewUnreadCount: function(){
    $.ajax({
      type: "POST",
      url:  "/message/unreadCount",
      dataType: "json",
      data: { },
      success: function(data){
        if (data[0].success == 'true'){
          if (data[0].message==0){
            $(".unreadCount").html("0");
            $(".hasUnreadMessage").removeClass("hasUnreadMessage");
          } else if (data[0].message>0) {
            $(".unreadCount").html(data[0].message);
            $(".messageLink").addClass("hasUnreadMessage");
          }
        }
        
        $(".loading_msg").hide();
      },
      error: function(){
        $(".loading_msg").hide();
      }
    });
  },
  
  
  /*
   * For the popup order request dialog
   */
  createOrderDialog: function(seller, itemtitle, itemid, price){
    messageUtil.orderFormLocked = true;
    messageUtil.sellerValue = seller;
    messageUtil.itemtitleValue = itemtitle;
    messageUtil.itemidValue = itemid;
    messageUtil.priceValue = price;
    messageUtil.quantityValue = 0;
    messageUtil.totalPriceValue = 0;
    
    messageUtil.createBackground();
    messageUtil.createOrderDialogContent(seller, itemtitle, itemid, price);
    messageUtil.centerDialog();
    
  },
  
  createOrderDialogContent: function(seller, title, itemid, price){
    var bgDiv = "<div class='popup-messageComposer'><div class='popup-messageComposerContainer'></div></div>";
    $("body").append( bgDiv );
    
    var dialogContent = "";
    dialogContent += "<div class='popupMessageTitle'>Create New Order</div><div class='popup-mainArea'>";
    dialogContent += messageUtil.createOrderInfoField(seller, title, itemid);
    dialogContent += messageUtil.createOrderQuantity(price) + "</div>";
    dialogContent += "<div class='popup-bottomControlArea'>" + messageUtil.createOrderButton() + "</div>";
    $(".popup-messageComposerContainer").append( dialogContent );
    
    // handlers
    $(".orderQuantity").keyup(function(){
      if(!isNaN($(this).val())){
        messageUtil.quantityValue = ($(this).val());
        messageUtil.totalPriceValue = (Number($(this).data('price'))*Number($(this).val())).toFixed(2);
        $(".orderTotalPrice").html( messageUtil.totalPriceValue );
      }
    }).blur(function(){
      if(isNaN($(this).val())){
        $(this).addClass("input_error");
      }else{
        $(this).removeClass("input_error");
      }
    });
    
    $(".confirmOrderButton").click(function(){
      messageUtil.sendOrderConfirmation();
    });
    
    $(".cancelOrderButton").click(function(){
      c = confirm("Are you sure to cancel the order?");
      if (c == true){
        $(".popup-backgroundAlpha").fadeOut();
        setTimeout("$('.popup-backgroundAlpha').remove()", 500);
        $(".popup-messageComposer").fadeOut();
        setTimeout("$('.popup-messageComposer').remove()", 500);
        
        messageUtil.formLocked = false;
      }
    });
  },
  
  createOrderInfoField: function(seller, title, itemid){
  
    var content = "<div class='messageFormField '><div class='messageAttrDesc'>Seller:</div>"
        + "<div class='messageAttrInput'><div class='staticValue'>"+ seller +"</div></div></div>";
        
    content += "<div class='messageFormField '><div class='messageAttrDesc'>Item:</div>"
        + "<div class='messageAttrInput'><div class='staticValue'>"+ title +"</div></div></div>";
    
    content += "<div class='messageFormField '><div class='messageAttrDesc'>Item ID:</div>"
        + "<div class='messageAttrInput'><div class='staticValue'>"+ itemid +"</div></div></div>";
    
    return content;
  },
  
  createOrderQuantity: function(price){
    var content = "<div class='messageFormField '><div class='messageAttrDesc'>Price:</div>"
        + "<div class='messageAttrInput'><div class='staticValue'>$ "+ price +" each</div></div></div>";
    content += "<div class='messageFormField '><div class='messageAttrDesc'>Quantity:</div>"
        + "<div class='messageAttrInput'><input type='text' class='orderQuantity' data-price='"+price+"' /></div></div>";
    content += "<div class='messageFormField '><div class='messageAttrDesc'>Total Price:</div>"
        + "<div class='messageAttrInput'><div class='staticValue orderTotalPrice'>Please enter quantity value</div></div></div>";
    
    return content;
  },
  
  createOrderButton: function(){
    var content = "<div class='messageFormField '><div class='messageAttrDesc'></div><div class='messageAttrInput'>"
        + "<span class='button linkButton confirmOrderButton'>Confirm Order</span> "
        + "<span class='button linkButton cancelOrderButton'>Cancel</span>"
        + "</div></div>";
    
    return content;
  },
  
  sendOrderConfirmation: function(){
  
    
    console.log( messageUtil.itemidValue );
    console.log( messageUtil.quantityValue );
    console.log( messageUtil.totalPriceValue );
  
    if(isNaN( messageUtil.quantityValue ) || messageUtil.quantityValue<=0){
      alert("Invalid quantity value");
      $(".orderQuantity").addClass("input_error");
      return;
    }
    
    // prevent double submission from UI
    if (messageUtil.sendLocked == true) return;
    
    messageUtil.sendLocked = true;
    
    var c = confirm("Are you sure to request to buy this item? Seller will be notified about this request!");
    
    if(c){
      $.ajax({
        type: "POST",
        url:  "/user/requestItem",
        dataType: "json",
        data: {
          "itemId": messageUtil.itemidValue,
          "quantity": messageUtil.quantityValue,
          "totalPrice": messageUtil.totalPriceValue,
        },
        success: function(data){
          if (data[0].success == 'true'){
            alert("Request is sent to item owner.")
            $(".popup-backgroundAlpha").fadeOut();
            setTimeout("$('.popup-backgroundAlpha').remove()", 500);
            $(".popup-messageComposer").fadeOut();
            setTimeout("$('.popup-messageComposer').remove()", 500);
            messageUtil.formLocked = false;
          }else{
            alert(data[0].message);
          }
          
          $(".loading_msg").hide();
          messageUtil.sendLocked = false;
        },
        error: function(){
          $(".loading_msg").hide();
          messageUtil.sendLocked = false;
        }
      });
    }
  },
  
  z:1
};


page.init();
messageUtil.init();



$(".removeFromWishListButton").live("click", function(){
  removeFromWishList( $(this).data("itemid") );
});

var removeFromWishList = function(itemid){
  $(".loading_msg").show();
  $.ajax({
    type: "POST",
    url:  "/user/removeFromWishlist",
    data: {
      itemId: itemid
    },
    success:function(xml){
      var status = $("success",xml).text();
      
      if(status == "true"){
        // TODO UI for status messages
        alert("item is removed from wishlist");
        $(".loading_msg").hide();
        
      }else{
        alert("Error occurred.");
        $(".loading_msg").hide();
        console.log(xml);
      }
      
    },
    error: function(){
      alert(_GENERAL_ERROR);
      $(".loading_msg").hide();
    }
  });
};


$(".addToWishListButton").live("click", function(){
  if (_LOGGED_IN == ""){
    // TODO UI for status messages
    alert("Please login to use this function.");
    return;
  }
  if (_USERTYPE == ""){
    // TODO UI for status messages
    alert("Hi visitor, please get a nickname to use this function.");
    return;
  }
  addToWishList( $(this).data("itemid") );
});

var addToWishList = function(itemid){
  $(".loading_msg").show();
  $.ajax({
    type: "POST",
    url:  "/user/addToWishlist",
    data: {
      itemId: itemid
    },
    success:function(xml){
      var status = $("success",xml).text();
      
      if(status == "true"){
        // TODO UI for status messages
        alert("Added to wishlist");
        $(".loading_msg").hide();
        
      }else{
        alert("Error occurred.");
        $(".loading_msg").hide();
        console.log(xml);
      }
      
    },
    error: function(){
      alert(_GENERAL_ERROR);
      $(".loading_msg").hide();
    }
  });
};



var composeSuccess = function(){
  alert("Message is sent");
};