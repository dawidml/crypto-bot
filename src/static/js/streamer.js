// streamer.js 
// handle stream

$(document).ready(function() {

	// set table sorting order
	$("table").tablesorter({
		sortList: [[3,1]],
	});

	startStream();
});


var config = {
	streamerUrl: 'http://127.0.0.1:5001',
	refreshing_time: 2000
};



String.prototype.format = function() {

    var formatted = this;

    for (var i = 0; i < arguments.length; i++) {
        var regexp = new RegExp('\\{'+i+'\\}', 'gi');
        formatted = formatted.replace(regexp, arguments[i]);
    }
    
    return formatted;
};


// connect to stream
var socket = io.connect(config.streamerUrl, {transports: ['websocket']});


/**
 * Set up the stream, handle messages.
 * 
 */
var startStream = function() {

	// handle messages
	socket.on("initial_prices", function(message) {
		console.log(message);

		createTable(message);

		var coinsCount = (Object.keys(message).length).toString();

		$('#date').text("Coins: {0}, Prices from: {1}".format(coinsCount, new Date().toUTCString()));

		refreshing();
	});

	socket.on("refreshing", function(data) {
		console.log(data);
		updateData(data);
	});

	socket.emit('init', '', function (data) { 
		console.log(data);
	});


	socket.on('reconnecting', 	function(m) { $.notify("Reconecting!", "error")});
   	socket.on('disconnect', 	function(m) { $.notify("Disconnected!", "error")});
   	socket.on('error', 			function(m) { $.notify(m, "error")});
   	socket.on('prices_warn', 	function(m) { $.notify("Couldn't load last prices", "warn")});

}


var refreshing = function() {

	setInterval(function(){ 
		socket.emit('refresh', '');
	}, config.refreshing_time);
}

/**
 * Check if there is information about price in response,
 * then get it and pass to make changes, sort table.
 * 
 * @param {string} message - request response
 */
var updateData = function(data) {

	$.each(data, function(key, value) {
		changeRow(key, value)
	});

	$.each($('table tr'), function(key, value) {
		
		var row = $(value);

		var spread = row.find('.spread');
		if(spread.text() == '0.00%') {
			row.hide();
		}
	});

	// sort table again
	$('table').trigger('update')
	
};


/**
 * Calculate current spread, refresh current price, call change colour.
 * 
 * @param {string} symbol - currency symbol
 * @param {float} price - new price
 */
var changeRow = function(symbol, price) {

	var row = $("#{0}".format(symbol));

	row.show();

	// get initial price of given currency
	var initialPrice = parseFloat(row.find('.initial').text());
	
	// calculate spread percentage
	// comparing to the initial price
	var spread = -(1- (price / initialPrice)) * 100;

	// when someting went wrong
	if(isNaN(spread)) return;

	// refresh current price
	$("#{0} .current".format(symbol)).text(price.toFixed(8));
	
	// set proper colour, adjust the value
	changeColour(spread.toFixed(2), row);
}

/**
 * Update spread, set proper colour etc.
 * 
 * @param {float} value - percentage difference betwen initial price and current.
 * @param {jQuery DOM} row - row to consider 
 */
var changeColour = function(value, row) {

	// element to change
	var spreadCell = row.find('.spread');
	
	// hghlight updated row
	row.effect("highlight", {}, 3000);

	// make value black again
	spreadCell.removeClass("green red");

	// add proper colour for value
	// and plus if it's positive
	if (value > 0) {

		spreadCell.addClass('green')
		value = "+{0}".format(value)

	} else if (value < 0){

		spreadCell.addClass('red')
	} 

	// set new spread value
	spreadCell.text("{0}%".format(value));
}


/**
 * Create table with considered currencies, initialize the values.
 *
 * @param {list} currencies - list of currencies with current prices.
 */
var createTable = function (currencies) {

	// table DOM element
	var tableBody = $('table tbody');

	// create table single row for each currency
	// initialize columns by current price
	// and spread as 0.00%
	$.each(currencies, function(key, value) {

		// create row DOM element
		var tr = $('<tr/>', {'id': key});
		
		var price = value[0].toFixed(8)
		// define parameters for each column
		var elements = [
			{'class': '', 'text': key},
			{'class': 'initial', 'text': price},
			{'class': 'current', 'text': price},
			{'class': 'spread', 'text': '0.00%'},
		];

		// add columns to row
		$.each(elements, function(key, value) {

			var td = $('<td/>', {'class': value.class, 'text': value.text}).appendTo(tr);
		});

		tr.appendTo(tableBody);

	}); 
}
