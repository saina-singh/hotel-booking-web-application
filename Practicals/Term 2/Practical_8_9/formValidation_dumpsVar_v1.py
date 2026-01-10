from flask import Flask, redirect, url_for, request, render_template
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('Formvalidation_v1.html')

@app.route ('/dumpVar', methods = ['POST', 'GET'])
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

if __name__ == '__main__':
   app.run (debug = True)
