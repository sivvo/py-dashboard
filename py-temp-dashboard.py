from flask import Flask, render_template, request, abort, jsonify
from flask_restful import Resource, Api
from flask_restful import reqparse
#from flask.ext.restful import reqparse
from sqlalchemy import create_engine, databases
from json import dumps
from flask_bootstrap import Bootstrap
import sqlalchemy
import sqlite3
from collections import defaultdict, OrderedDict
from datetime import timedelta, datetime
import time
import urllib
import urllib2
import json

#e = create_engine('sqlite:///weatherlog.db')
app = Flask(__name__)
api = Api(app)
bootstrap = Bootstrap(app)
#DATABASE="d:\\dev\\py-temp-dashboard\\weatherlogger.db"
DATABASE="/media/martin/d/dev/py-temp-dashboard/weatherlogger.db"
#DATABASE="/home/pi/dashboard/weatherlogger.db"

class Temps():
    def __init__(self):
        self.db = sqlite3.connect(DATABASE)
        self.db.text_factory = str
        self.configure_database()  # create the sqlite DB if it doesn't exist


    def db_query(self, query, params=""):
        #db = sqlite3.connect("weatherlogger.db")
        db = sqlite3.connect(DATABASE)
        db.text_factory = str
        cursor = db.cursor()
        response = cursor.execute(query, params)
        #db.close()
        return response


    def configure_database(self):
        try:
            self.db_query("Select count(*) from weather_logger")
        except sqlite3.OperationalError:
            schema = """
            CREATE TABLE weather_logger
            (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    location varchar(30) NOT NULL,
                    timestamp DATETIME,
                    temperature FLOAT,
                    humidity FLOAT,
                    lux INTEGER,
                    min FLOAT,
                    max FLOAT,
                    sunrise varchar(8),
                    sunset varchar(8)
                    )
            """
            self.db_query(schema)


    def write_sensor_data(self, sensor_data):
        location = sensor_data["sensor"]
        timestamp = sensor_data["timestamp"]
        temperature = sensor_data["temperature"]
        try:
            humidity = sensor_data["humidity"]
        except:
            humidity = ""
        try:
            lux = sensor_data["lux"]
        except:
            lux = ""
        try:
            min = sensor_data["min_temp"]
        except:
            min = ""
        try:
            max = sensor_data["max_temp"]
        except:
            max = ""
        try:
            sunrise = sensor_data["sunrise"]
        except:
            sunrise = ""
        try:
            sunset = sensor_data["sunset"]
        except:
            sunset = ""
        db = sqlite3.connect(DATABASE)
        db.text_factory = str
        cursor = db.cursor()
        db.row_factory = sqlite3.Row
        querystr = "INSERT INTO weather_logger ( location, timestamp, temperature, humidity, " \
                   "lux, min, max, sunrise, sunset) VALUES (?,?,?,?,?,?,?,?,?)"
        try:
            status = 0
            status_txt = ""
            result = cursor.execute(querystr, [location,timestamp,temperature,humidity,lux,min,max,sunrise,sunset])
            db.commit()
        except sqlite3.Error as er:
            status = 1
            status_txt = er.message
        return status, status_txt



    def calc_temps(self, sensor):
        from_time = time.time() - 1604800
        querystr = """
        SELECT 
            ROUND(COALESCE(min,min(temperature)),1) min_temp, ROUND(COALESCE(max,max(temperature))) max_temp
        FROM weather_logger
        where location = ? 
        AND timestamp >= ? 
        GROUP BY location
        """

        print querystr, sensor, from_time

        cursor = self.db_query(querystr, [sensor,from_time])
        result = cursor.fetchall()
        print result

        return result


    """
    get the latest record from all sensors... okay?
    """
    def get_sensor_data(self):
        querystr = """
            SELECT DISTINCT location, timestamp, round(temperature,1), round(humidity,1), round(lux,1) 
            FROM weather_logger 
            GROUP BY location 
            ORDER BY timestamp DESC;
        """
        cursor = self.db_query(querystr)
        result = cursor.fetchall()
        return result


temps = Temps()

@app.route('/channel/<username>')
def channel(username):
    return render_template('username.html', username=username)

@app.route('/api/sensor', methods=['POST'])
def api_sensor():

    if request.method == 'POST':
        sensor_data = request.form
        if "sensor" not in request.form or "timestamp" not in request.form:
            # these fields are mandatory
            print "sensor/timestamp must be set"
            return jsonify("{status: error, message: 'sensor and timestamp are required fields' }", 400)
        else:
            # 0: okay, 1: error
            status, message = temps.write_sensor_data(sensor_data)

            print status, message
            if status ==0:
                # all good
                return jsonify("{status: success, message: '' }",200)
            else:
                print "error ", message

                return jsonify("{status: error, message: '"+message+"' }",400)

    else:
        return jsonify("{status: error, message: 'use POST' }", 400)

@app.route('/')
def homepage():
    # right now, the sensor data is hard coded. we need to get it all from the DB
    data = temps.get_sensor_data()
    sensors = []
    sensor_data = {}
    sensor_data = defaultdict(dict)

    for row in data:
        name = row[0]
        timestamp =row[1]
        temperature = row[2]
        humidity = row[3]
        lux = row[4]
        calculated_temps = temps.calc_temps(name)

        print name, timestamp, humidity, lux, calculated_temps
        print type(calculated_temps)
        print calculated_temps[0]


        min_temp = calculated_temps[0][0]
        max_temp = calculated_temps[0][1]
        sensors.append(name)
        sensor_data[name]["current_temperature"] = temperature
        sensor_data[name]["min_temperature"] = min_temp
        sensor_data[name]["max_temperature"] = max_temp
        sensor_data[name]["relative_humidity"] = humidity
        sensor_data[name]["lux"] = lux
        sensor_data[name]["name"] = name
    #sensor_data = sorted(sensor_data)

    #sensors = ['sensor1', 'sensor2', 'sensor3', 'sensor4', 'sensor5', 'sensor6']
#    sensor_data = {
 #       'room name': {'current_temperature': 21, 'min_temperature': 7, 'max_temperature': 23, 'relative_humidity': 77, 'lux':1, 'name': "Hallway"},
  #      'office': {'current_temperature': 22, 'min_temperature': 17, 'max_temperature': 25, 'relative_humidity': 70, 'lux': 2, 'name': "Living Room"},
   #     'sensor3': {'current_temperature': 21, 'min_temperature': 16, 'max_temperature': 23, 'relative_humidity': 77,'lux': 2, 'name': "Office"},
    #    'sensor4': {'current_temperature': 24, 'min_temperature': 20, 'max_temperature': 27, 'relative_humidity': 80,'lux': 2, 'name': "Bedroom"},
     #   'sensor5': {'current_temperature': -1, 'min_temperature': -3, 'max_temperature': 8, 'relative_humidity': 44,'lux': 3, 'name': "Balcony"},
      #  'sensor6': {'current_temperature': -1, 'min_temperature': -7, 'max_temperature': 8, 'relative_humidity': 44, 'lux': 3, 'name': "outside"}}
    try:
        #temps = [21, 7, 23, 77, 1, "Hallway"],[22, 17, 25, 70, 2, "Living Room"], [21, 16, 23, 77, 2, "Office"], [24, 20, 27, 80, 2, "Bedroom"], [-1, -3, 3, 40, 3, "Balcony"], [-1, -7, 8, 44, 3, "Outside"]
        return render_template("dashboard.html", sensors=sensors,sensor_data=sensor_data)
    except Exception, e:
        return str(e)

def time_converter(time):
    converted_time = datetime.fromtimestamp(
        int(time)
    ).strftime('%I:%M %p')
    return converted_time

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/about')
def aboutpage():

    title = "About this site"
    paragraph = ["blah blah blah memememememmeme blah blah memememe"]

    pageType = 'about'

    return render_template("index.html", title=title, paragraph=paragraph, pageType=pageType)

@app.route('/about/contact')
def contactPage():

    title = "About this site"
    paragraph = ["blah blah blah memememememmeme blah blah memememe"]

    pageType = 'about'

    return render_template("index.html", title=title, paragraph=paragraph, pageType=pageType)


def hello_world():
    return 'Hello World!'


if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')
