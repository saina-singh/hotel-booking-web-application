from flask import Flask, request, render_template

app = Flask(__name__)

@app.route('/')	# This is kind of index route and accessed when app loads in a browser
def index():	# gets all distinc list of cities from DB and passes to html template for dynamic web page generation
	return render_template('datepicker_clean.html')

#This route is a generic route and displays all the received data.. good for testing
@app.route ('/dumpsVar/', methods = ['POST', 'GET'])
def dumpVar():
	if request.method == 'POST':
		result = request.form
		output = "<H2>Data Received: </H2></br>"
		output += "Number of Data Fields : " + str(len(result))
		for key in list(result.keys()):
			output = output + " </br> " + key + " : " + result.get(key)
		return output
	else:
		result = request.args
		output = "<H2>Data Received: </H2></br>"
		output += "Number of Data Fields : " + str(len(result))
		for key in list(result.keys()):
			output = output + " </br> " + key + " : " + result.get(key)
		return output  

#Running this script as a standalone webapp
if __name__ == '__main__':
   app.run (debug = True)


