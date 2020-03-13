from flask import Flask, request, Response
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.viber_requests import ViberMessageRequest
from viberbot.api.viber_requests import ViberConversationStartedRequest
from viberbot.api.messages import KeyboardMessage
from Settings import TOKEN
import json
import random
import datetime
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column
from sqlalchemy import Integer, String, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.pool import NullPool

with open('english_words.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

app = Flask(__name__)

bot_configuration = BotConfiguration(
    name='OrcaVV',
    avatar='http://viber.com/avatar.jpg',
    auth_token=TOKEN
)

viber = Api(bot_configuration)

engine = create_engine("postgres://zjguzaoffvbgzj:57e92920b8896da21387e6977b7f39510dacb38808c786b751888389272b79de@ec2-54-247-169-129.eu-west-1.compute.amazonaws.com:5432/dealhb2vdnm1f6", poolclass=NullPool)

Base = declarative_base()

Session = sessionmaker(engine)


class Users(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True)
    fio = Column(String, nullable=False, default='John Doe')
    viber_id = Column(String, nullable=False, unique=True)
    t_last_answer = Column(DateTime)
    t_alert = Column(DateTime)

    words = relationship("Learning", back_populates='user')

    def __repr__(self):
        return f'{self.user_id}: {self.fio}[{self.viber_id}]'


class Learning(Base):
    __tablename__ = 'learning'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    word = Column(String, nullable=False)
    correct_answer = Column(Integer, nullable=False, default=0)
    t_last_correct_answer = Column(DateTime)

    user = relationship("Users", back_populates='words')

    def __pepr__(self):
        return f'{self.id}: {self.user_id}[{self.word} / {self.right_answer}]'



class Game:
    def __init__(self, viber_id):
        self.viber_id = viber_id
        self.word = {}
        self.count_all = 0
        self.count_correct = 0


START_KBD = {
    "Type": "keyboard",
    "Buttons": [
        {
            "Columns": 6,
            "Rows": 1,
            "BgColor": "#e6f5ff",
            "BgMedia": "http://link.to.button.image",
            "BgMediaType": "picture",
            "BgLoop": True,
            "ActionType": "reply",
            "ActionBody": "Старт",
            "ReplyType": "message",
            "Text": "Старт"
        }
    ]
}

message = KeyboardMessage(tracking_data='tracking_data', keyboard=START_KBD)


def next_word(game):
    session = Session()
    user_id = session.query(Users.user_id).filter(Users.viber_id == game.viber_id)
    game.word = data[random.choice(range(50))]
    query = session.query(Learning).filter(Learning.user_id == user_id).filter(Learning.word == game.word["word"])
    learning = query.all()
    if len(learning) == 0:
        session.add(Learning(user_id=user_id, word=game.word["word"]))
        session.commit()
    else:
        correct_answer = session.query(Learning.correct_answer).filter(Learning.user_id == user_id).filter(
            Learning.word == game.word["word"]).first()
        if correct_answer >= 3:
            next_word(game)
    session.close()

# вопрос
def question(game):
    session = Session()

    if game.count_all <= 3:
        # вывести вопрос
        next_word(game)
        bot_response = TextMessage(text=f'{game.count_all + 1}. Перевод слова: {game.word["word"]}',
                                   keyboard=CreateKBD(game), tracking_data='tracking_data')
        viber.send_messages(game.viber_id, [bot_response])
    else:
        # вывести итоги раунда
        bot_response = TextMessage(text=f"Верно {game.count_correct} из {game.count_all}", keyboard=START_KBD,
                                   tracking_data='tracking_data')
        viber.send_messages(game.viber_id, [bot_response])
	session.close()

# обработать ответ
def answer(text, game):
    session = Session()
    if text == game.word["translation"]:
        # счётчик правильных ответов
        game.count_correct += 1
        user_id = session.query(Users.user_id).filter(Users.viber_id == game.viber_id)
        learning = session.query(Learning).filter(Learning.user_id == user_id).filter(
            Learning.word == game.word["word"]).first()
        learning.correct_answer += 1
        session.commit()
        bot_response = TextMessage(text='Правильно')
    else:
        bot_response = TextMessage(text='Неправильно')
    # всего ответов
    game.count_all += 1
    viber.send_messages(game.viber_id, [bot_response])
	session.close()
    question(game)
	

# привести пример
def example(game, number):
    session = Session()
    bot_response = TextMessage(text=f'{game.word["examples"][number]}',
                               keyboard=CreateKBD(game), tracking_data='tracking_data')
    keyboard = KeyboardMessage(tracking_data='tracking_data', keyboard=CreateKBD(game))
    viber.send_messages(game.viber_id, [bot_response])
	session.close()


# клавиатура ползователя
def CreateKBD(game):
    session = Session()
    # список с вариантами переводов слова
    translation = []
    # правильный перевод
    translation.append(game.word["translation"])
    while len(translation) != 4:
        # заносим новое слово если его нет в списке
        if random.choice(data)["translation"] not in translation:
            translation.append(random.choice(data)["translation"])
        random.shuffle(translation)
    KEYBOARD = {
        "Type": "keyboard",
        "Buttons": [
            {
                "Columns": 3,
                "Rows": 1,
                "BgColor": "#e6f5ff",
                "BgMedia": "http://link.to.button.image",
                "BgMediaType": "picture",
                "BgLoop": True,
                "ActionType": "reply",
                "ActionBody": f"{translation[0]}",
                "ReplyType": "message",
                "Text": f"{translation[0]}"
            },
            {
                "Columns": 3,
                "Rows": 1,
                "BgColor": "#e6f5ff",
                "BgMedia": "http://link.to.button.image",
                "BgMediaType": "picture",
                "BgLoop": True,
                "ActionType": "reply",
                "ActionBody": f"{translation[1]}",
                "ReplyType": "message",
                "Text": f"{translation[1]}"
            },
            {
                "Columns": 3,
                "Rows": 1,
                "BgColor": "#e6f5ff",
                "BgMedia": "http://link.to.button.image",
                "BgMediaType": "picture",
                "BgLoop": True,
                "ActionType": "reply",
                "ActionBody": f"{translation[2]}",
                "ReplyType": "message",
                "Text": f"{translation[2]}"
            },
            {
                "Columns": 3,
                "Rows": 1,
                "BgColor": "#e6f5ff",
                "BgMedia": "http://link.to.button.image",
                "BgMediaType": "picture",
                "BgLoop": True,
                "ActionType": "reply",
                "ActionBody": f"{translation[3]}",
                "ReplyType": "message",
                "Text": f"{translation[3]}"
            },
            {
                "Columns": 6,
                "Rows": 1,
                "BgColor": "#e6f5ff",
                "BgMedia": "http://link.to.button.image",
                "BgMediaType": "picture",
                "BgLoop": True,
                "ActionType": "reply",
                "ActionBody": "Пример использования",
                "ReplyType": "message",
                "Text": "Пример использования"
            }
        ]
    }
    return KEYBOARD


# справочник соответствия пользователя и его текущей игры
game_usera = {}


def poisk(viber_id):
    return game_usera[viber_id]


# количество примеров перевода
count_example = 0


@app.route('/incoming', methods=['POST'])
def incoming():
    Base.metadata.create_all(engine)
    # обработка
    session = Session()
    viber_request = viber.parse_request(request.get_data())

    if isinstance(viber_request, ViberConversationStartedRequest):
        viber_user = viber_request.user.id
        if len(session.query(Users).filter(Users.viber_id == viber_user).all()) == 0:
            add_user = Users(fio=viber_request.user.name, viber_id=viber_user, t_last_answer=datetime.datetime.now())
            session.add(add_user)
            session.commit()
        new_game = Game(viber_user)
        game_usera[viber_user] = new_game
        user_id = session.query(Users.user_id).filter(Users.viber_id == game_usera[viber_user].viber_id)
        count_correct = session.query(Learning).filter(Learning.user_id == user_id).filter(
            Learning.correct_answer > 5).count()
        last_visit = session.query(Users.t_last_answer).filter(Users.user_id == user_id).first()
        text = "Hello! Let's learn English \n" \
               f'Нажмите старт. Вы выучили {count_correct} слов \n' \
               f'Время последнего посещения {last_visit}'
        viber.send_messages(viber_user, [TextMessage(text=text, keyboard=START_KBD,
                                                     tracking_data='tracking_data')])
    if isinstance(viber_request, ViberMessageRequest):
        user = session.query(Users).filter(Users.viber_id == viber_request.sender.id).first()
        game = poisk(user.viber_id)
        if isinstance(viber_request.message, TextMessage):
            if viber_request.message.text == "Старт":
                user.t_last_answer = datetime.datetime.now()
                user.t_alert = datetime.datetime.now() + datetime.timedelta(minutes=10)
                session.commit()
                game.count_all = 0
                game.count_correct = 0
                question(game)
            # вызов примера использования
            elif viber_request.message.text == "Пример использования":
                global count_example
                example(game, count_example)
                # проверяем количетво примеров
                if count_example > len(game.word["examples"]):
                    count_example = 0
                else:
                    count_example += 1
            elif viber_request.message.text == 'Напомнить позже':
                user.t_alert = datetime.datetime.now() + datetime.timedelta(minutes=10)
                session.commit()
            else:
                # ответ пользователя
                answer(viber_request.message.text, game)
	session.close()
	
    return Response(status=200)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=80)
