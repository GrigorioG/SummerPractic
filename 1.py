import json
import telebot
import requests
import bs4
import pandas as pd
from bs4 import BeautifulSoup

# введите сюда ваш телеграм-токен
bot = telebot.TeleBot('1935854365:AAGeWF4Dut2bopAdLkpE6LioheRY-FTJRg0')

#введите сюда ваш токен Aviasales
av_api_token = "8d574f375838d8bad87159110cb48aa9"

# получает словари:
# из названия города в код города
# из названия города в Alpha2 код страны, в которой этот город находится
def Get_cities_dicts():
    cities_json = requests.get("https://api.travelpayouts.com/data/ru/cities.json").text
    cities = json.loads(cities_json)

    city_names = list()
    city_codes = list()
    country_codes = list()

    for city in cities:
        city_names.append(city['name'])
        city_codes.append(city['code'])

        country_codes.append(city['country_code'])

    city_name_to_code = dict(zip(city_names, city_codes))
    city_name_to_short_country_code = dict(zip(city_names, country_codes))

    return city_name_to_code, city_name_to_short_country_code

# получает словарь из кода авиакомпании в ее название
def Get_airlines_dict() -> dict:
    airlines_json = requests.get("https://api.travelpayouts.com/data/ru/airlines.json").text
    airlines = json.loads(airlines_json)
    airline_names = list()
    airline_codes = list()
    for airline in airlines:
        airline_names.append(airline['name_translations']['en'])
        airline_codes.append(airline['code'])
    code_to_airline_name = dict(zip(airline_codes, airline_names))
    return code_to_airline_name



class AirplaneTicketsFinder:

    def __init__(self, av_token):
        self.av_token = av_token
        self.city_name_to_code, self.city_name_to_country_code = Get_cities_dicts()
        self.code_to_airline_name = Get_airlines_dict()

    def __call__(self, origin_city, destination_city, depart_date, return_date) -> str:

        if origin_city in self.city_name_to_code:
            origin = self.city_name_to_code[origin_city]
        else:
            return "Ошибка в названии вашего города"

        if destination_city in self.city_name_to_code:
            destination = self.city_name_to_code[destination_city]
        else:
            return "Ошибка в названии города куда вы хотите отправиться"

        url = f"http://api.travelpayouts.com/v1/prices/direct?origin={origin}&destination={destination}&depart_date={depart_date}&return_date={return_date}&token={self.av_token}"
        response = requests.get(url)

        if json.loads(response.text)["success"] == "false":
            return "Даты введены некорректно"

        if json.loads(response.text)['data'] == {}:
            return "К сожалению отправиться в данный город в эти даты невозможно"

        my_ticket = json.loads(response.text)['data'][destination]['0']

        code_of_airline = my_ticket['airline']
        airline_name = self.code_to_airline_name[code_of_airline]
        price = my_ticket['price']
        flight_number = my_ticket['flight_number']
        time_of_depart = my_ticket['departure_at'].split(sep="T")[1][:8]
        time_of_return = my_ticket['return_at'].split(sep="T")[1][:8]
        day_of_expiry = my_ticket['expires_at'].split(sep="T")[0]

        return f"Предлагаю вот такой билет:\n" \
               f"авиокомпания: {airline_name}\n" \
               f"цена: {price} руб\n" \
               f"номер вылета: {flight_number}\n" \
               f"время вылета самолета туда: {time_of_depart}\n" \
               f"время вылета самолета обратно: {time_of_return}\n" \
               f"билет можно приобрести до {day_of_expiry}\n"


def CovidStaticticFinder() -> str:
    url = "https://index.minfin.com.ua/reference/coronavirus/geography/"
    response = requests.get(url)

    soup = BeautifulSoup(response.content, 'html.parser')
    countries_information = soup.find("table", "line").find_all("tr")[2:]

    countries_information = countries_information[:10] + countries_information[11:199] + countries_information[202:]

    country_names = list()
    total_cases = list()
    total_deaths = list()
    total_recovered = list()
    active_cases = list()

    for country in countries_information:
        country_names.append(country.find_all("td")[0].text)
        total_cases.append(country.find_all("td")[1].text)
        total_deaths.append(country.find_all("td")[3].text)
        total_recovered.append(country.find_all("td")[5].text)
        active_cases.append(country.find_all("td")[7].text)

    df = pd.DataFrame(
        {
            'country_name': country_names,
            'total_cases': total_cases,
            'total_deaths': total_deaths,
            'total_recovered': total_recovered,
            'active_cases': active_cases
        }
    )

    country_information = df[df.country_name == name_of_destination_country_].iloc[0]

    return f"Статистика коронавируса в стране, в которую ты летишь ({name_of_destination_country_})\n" \
           f"всего заражений: {country_information.total_cases}\n" \
           f"смертельные случаи: {country_information.total_deaths}\n" \
           f"выздоровевшиеа: {country_information.total_recovered}\n" \
           f"сейчас болеют: {country_information.active_cases}\n"



name_of_destination_country_ = ""
origin_city_ = ""
destination_city_ = ""
depart_date_ = ""
return_date_ = ""

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет, если хочешь куда-то слетать, то введи название города, откуда ты хочешь отправиться")

@bot.message_handler(content_types=['text'])
def request(message):
    global origin_city_
    global destination_city_
    global depart_date_
    global return_date_
    global av_api_token_
    global name_of_destination_country_

    if origin_city_ == "":
        origin_city_ = message.text.strip()
        bot.send_message(message.chat.id, f"Теперь введи название страны, куда хочешь отправиться")
    elif name_of_destination_country_ == "":
        name_of_destination_country_ = message.text.strip()
        bot.send_message(message.chat.id, f"Теперь введи название города, куда хочешь отправиться")
    elif destination_city_ == "":
        destination_city_ = message.text.strip()
        bot.send_message(message.chat.id, f"Теперь введи дату отправления в формате гггг-мм-дд")
    elif depart_date_ == "":
        depart_date_ = message.text.strip()
        bot.send_message(message.chat.id, f"Теперь введи дату возвращения в формате гггг-мм-дд")
    else:
        return_date_ = message.text.strip()
        bot.send_message(message.chat.id, "Подождите пару минут...")

        TicketsFinder = AirplaneTicketsFinder(av_api_token)
        ticket = TicketsFinder(origin_city_, destination_city_, depart_date_, return_date_)
        bot.send_message(message.chat.id, ticket)

        if len(ticket) > 60:
            covid_statistic = CovidStaticticFinder()
            bot.send_message(message.chat.id, covid_statistic)

        name_of_destination_country_ = ""
        origin_city_ = ""
        destination_city_ = ""
        depart_date_ = ""
        return_date_ = ""

        bot.send_message(message.chat.id, "Если хочешь еще куда-то слетать, то введи название города, откуда ты хочешь отправиться")


bot.polling()
