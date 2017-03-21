/*
This is the MexicoEn140 main app.
Its structure/procedure is as follows:

	1. invoke libs
	2. configure express
	3. routings || passing by index.html plus json in 
	4. app listen

*/


// 1. invoke libs
var port = (process.env.PORT || 8080),
	express = require('express'),
    path = require('path'),
    auth = require('http-auth'),
    serveIndex = require('serve-index');    
var adminUser = 'logviewer';
var adminPassword = '1qazxsw2*';

// 3. Basic authentication
var basic = auth.basic({
        realm: "MexicoEn140",
    }, function (username, password, callback) { // Custom authentication method.
        callback(username === adminUser && password === adminPassword);
    }
);

var authMiddleware = auth.connect(basic);
// 2. express app basic config
var app = express();
app.use(express.static(__dirname + '/public'));

// 7. routings
app.use('/debug/logs/python', authMiddleware, serveIndex(path.join(__dirname, '/../AppPython/logs')));
app.use('/debug/logs/python', authMiddleware, express.static(path.join(__dirname, '/../AppPython/logs'), { 'index': false }));
// 8. app listening
app.listen(port);
console.log("\t Mexico en 140 running on port :: " + port);