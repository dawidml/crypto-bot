from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from flask import Flask
from flask_socketio import SocketIO
import lxml.html
import time


app = Flask(__name__)
socket = SocketIO(app, logger=True, engineio_logger=True)
scrapper = None


class Scrapper:

	url = 'https://yobit.net/en/'
	table_container = "//table[@id='trade_market']//tbody"
	button_container = '/html/body/div[1]/main/div/div[1]/div[2]/div[2]/div/a[2]'

	timeout = 10	

	price_min = 0.0000005
	price_max = 0.01


	def __init__(self) -> None:
		
		self.driver = None
		self.table = None
		self.initial_prices = dict()

		self.coins = []


	def init(self) -> None :

		try:

			# uncomment to use chrome in headless mode 
			# so additional browser won't start 

			# options = Options()
			# options.headless = True
			# self.driver = webdriver.Chrome(options=options, executable_path='chromedriver')

			# may vary depending on OS (tested on linux) 
			self.driver = webdriver.Firefox(executable_path='/bin/geckodriver')

			self.make_connection()

		except Exception as e:

			print('%s Please run app again.' % e)


	def make_connection(self) -> None:

		if self.driver is None:
			raise ValueError('Driver is not loaded! Please make sure\
				that Firefox is installed and geckodriver.exe file exists.')

		try:
			self.driver.get(self.url)
		except:
			raise AttributeError('Driver is not loaded! Please make sure\
				that Firefox is installed and geckodriver.exe file is\
				in that directory.')

		time.sleep(self.timeout)

		if not self.element_exist(self.table_container):
			raise AttributeError("Couldn't find coins table. It might be\
				caused by slow internet connection or change of div element.")

		if not self.element_exist(self.button_container):
			raise AttributeError("Couldn't find BTC button. It might be\
				caused by slow internet connection or change of div element.")

		# click btc button to get access to coins table
		self.driver.find_element_by_xpath(self.button_container).click()

		# keep table DOM element as a class member
		self.table = self.driver.find_element_by_xpath(self.table_container)


	def element_exist(self, xpath: str) -> bool:
		
		try:
			element_present = EC.presence_of_element_located((By.XPATH, xpath))
			WebDriverWait(self.driver, self.timeout).until(element_present)
			return True
		except:
			return False


	def calculate_initial_prices(self) -> None:

		try:
			initial_prices = self.get_prices()
		except:
			print('An error occured during the initialization the prices. \
				Please check the internet connection and run app again.')
			return

		coins_to_remove = []

		for symbol, price in initial_prices.items():

			# remove coins which are out of considered range
			if self.price_in_range(price):
				continue

			coins_to_remove.append(symbol)

		# keep coins to consider
		self.coins = list(initial_prices.keys() - set(coins_to_remove))

		# keep initial prices - add second value which is current price
		# the second value will change during refreshing
		self.initial_prices = {
			k: 2 * [initial_prices[k]] for k in initial_prices \
			if k not in coins_to_remove
		}


	def price_in_range(self, price: float) -> bool:

		return self.price_min < price < self.price_max


	def get_prices(self) -> dict:

		coins_price = {}

		html = self.table.get_attribute('innerHTML')

		# lxml is much faster than selenium and bs4
		rows = lxml.html.fromstring(html)

		for row in rows:

			symbol = row[0].text_content()
			price = row[1].text_content()

			# parse from string to float
			price = float(price)

			# if coins list is empty 
			# load initial coins with prices
			if not len(self.coins):
				coins_price[symbol] = price
				continue

			# new coin - do not consider
			if not symbol in self.coins:
				continue

			# skip if price didn't change 
			if price == self.initial_prices[symbol][1]:
				continue

			# update last price in the collection
			self.initial_prices[symbol][1] = price
			
			# add change to collection
			coins_price[symbol] = price

		return coins_price


@socket.on('init')
def send_init(message):

	try:
		scrapper.calculate_initial_prices()
		socket.emit('initial_prices', scrapper.initial_prices)

	except:
		socket.emit('error', 'Initialization error! Please check \
			the internet connection and run app again.')


@socket.on('refresh')
def send_init(message):

	try:
		prices = scrapper.get_prices()
		
		if not prices:
			return

		socket.emit('refreshing', prices)

	except:
			
		print('An error occured during the loading the new prices. Please \
			check the internet connection or your browser.')

		socket.emit('prices_warn', 'Something went wrong!')


if __name__ == '__main__':
	
	scrapper = Scrapper()
	scrapper.init()	

	socket.run(app, host='127.0.0.1', port=5001)