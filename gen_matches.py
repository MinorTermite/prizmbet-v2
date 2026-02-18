import json, datetime, random, os

now = datetime.datetime.now()
months_ru = {1:'янв',2:'фев',3:'мар',4:'апр',5:'май',6:'июн',
             7:'июл',8:'авг',9:'сен',10:'окт',11:'ноя',12:'дек'}

def fmt_date(dt):
    return f'{dt.day} {months_ru[dt.month]}'

def rand_odds():
    p1 = round(random.uniform(1.5, 4.5), 2)
    p2 = round(random.uniform(1.5, 4.5), 2)
    x  = round(random.uniform(2.8, 4.2), 2)
    p1x = round(p1*0.5+0.8, 2)
    p12 = round(min(p1,p2)*0.6+0.7, 2)
    px2 = round(p2*0.5+0.8, 2)
    return {'p1':str(p1),'x':str(x),'p2':str(p2),'p1x':str(p1x),'p12':str(p12),'px2':str(px2)}

# Смещение в часах от момента запуска (MIN_OFFSET = минимум через сколько часов первый матч)
MIN_OFFSET = 6  # первые матчи через 6 часов, чтобы они не "прошли"

raw = [
  # sport, league, id_base, team1, team2, hours_from_now
  ('hockey','НХЛ','НХЛ_ТОР_БОС','Торонто','Бостон', MIN_OFFSET),
  ('football','Лига чемпионов УЕФА','ЛИГ_ГАЛ_ЮВЕ','Галатасарай','Ювентус', MIN_OFFSET+2),
  ('esports','CS2. Major','CS2_CLO_HER','Cloud9','Heroic', MIN_OFFSET),
  ('hockey','КХЛ','КХЛ_ДИН_АКБ','Динамо Москва','Ак Барс', MIN_OFFSET+3),
  ('basket','NBA','НБА_МАЙ_МИЛ','Майами','Милуоки', MIN_OFFSET+4),
  ('basket','Евролига','МАТ_РЕА_БАР_Е','Реал Мадрид','Барселона', MIN_OFFSET+16),
  ('football','Лига Европы УЕФА','ЛЕУ_СЕВ_ЛЕЙ','Севилья','Лейпциг', MIN_OFFSET+18),
  ('hockey','НХЛ','НХЛ_ЭДМ_КАЛ','Эдмонтон','Калгари', MIN_OFFSET+20),
  ('football','Испания. Ла Лига','МАТ_РЕА_БЕТ','Реал Сосьедад','Бетис', MIN_OFFSET+24),
  ('football','Россия. Премьер-лига','РПЛ_КРА_ЛОК','Краснодар','Локомотив', MIN_OFFSET+24),
  ('esports','Dota 2. Мажор','DOT_TEA_PSG','Team Liquid','PSG.LGD', MIN_OFFSET+27),
  ('basket','NBA','НБА_ЛЕЙ_БОС','Лейкерс','Бостон', MIN_OFFSET+40),
  ('basket','Евролига','МАТ_ЦСК_ПАН','ЦСКА','Панатинаикос', MIN_OFFSET+41),
  ('football','Англия. Премьер-лига','АПЛ_НЬЮ_БРА','Ньюкасл','Брайтон', MIN_OFFSET+43),
  ('football','Испания. Ла Лига','МАТ_АТЛ_СЕВ','Атлетико','Севилья', MIN_OFFSET+48),
  ('esports','Dota 2. Мажор','DOT_TUN_GAI','Tundra','Gaimin Gladiators', MIN_OFFSET+63),
  ('football','Англия. Премьер-лига','АПЛ_ЛИВ_ЧЕЛ','Ливерпуль','Челси', MIN_OFFSET+66),
  ('football','Англия. Премьер-лига','АПЛ_АСТ_ВЕС','Астон Вилла','Вест Хэм', MIN_OFFSET+67),
  ('hockey','НХЛ','НХЛ_РЕЙ_ДЬЯ','Рейнджерс','Дьяволс', MIN_OFFSET+68),
  ('esports','Dota 2. Мажор','DOT_TEA_OG','Team Spirit','OG', MIN_OFFSET+69),
  ('esports','CS2. Major','CS2_NAT_FAZ','Natus Vincere','FaZe Clan', MIN_OFFSET+88),
  ('football','Италия. Серия A','МАТ_ИНТ_МИЛ','Интер','Милан', MIN_OFFSET+89),
  ('football','Англия. Премьер-лига','АПЛ_МАН_ТОТ','Манчестер Юнайтед','Тоттенхэм', MIN_OFFSET+90),
  ('football','Лига чемпионов УЕФА','ЛИГ_РЕА_БАВ','Реал Мадрид','Бавария', MIN_OFFSET+92),
  ('hockey','НХЛ','НХЛ_ВЕГ_КОЛ','Вегас','Колорадо', MIN_OFFSET+92),
  ('football','Испания. Ла Лига','МАТ_РЕА_БАР','Реал Мадрид','Барселона', MIN_OFFSET+94),
  ('football','Англия. Премьер-лига','АПЛ_МАН_АРС','Манчестер Сити','Арсенал', MIN_OFFSET+109),
  ('basket','NBA','НБА_БРУ_ФИЛ','Бруклин','Филадельфия', MIN_OFFSET+111),
  ('football','Лига Европы УЕФА','ЛЕУ_МАН_РОМ','Манчестер Юнайтед','Рома', MIN_OFFSET+127),
  ('hockey','КХЛ','КХЛ_СПА_ЛОК','Спартак','Локомотив', MIN_OFFSET+129),
  ('football','Россия. Премьер-лига','РПЛ_ЦСК_ДИН','ЦСКА','Динамо', MIN_OFFSET+131),
  ('basket','Евролига','МАТ_ФЕН_ОЛИ','Фенербахче','Олимпиакос', MIN_OFFSET+135),
  ('football','Германия. Бундеслига','МАТ_ЛЕЙ_БАЙ','Лейпциг','Байер', MIN_OFFSET+139),
  ('esports','CS2. Major','CS2_GES_TEA','G2 Esports','Team Vitality', MIN_OFFSET+153),
  ('football','Лига Европы УЕФА','ЛЕУ_АТА_БАЙ','Аталанта','Байер', MIN_OFFSET+155),
  ('football','Германия. Бундеслига','МАТ_БАВ_БОР','Бавария','Боруссия', MIN_OFFSET+155),
  ('esports','CS2. Major','CS2_MOU_FNA','MOUZ','Fnatic', MIN_OFFSET+156),
  ('football','Лига чемпионов УЕФА','ЛИГ_МАН_ИНТ','Манчестер Сити','Интер', MIN_OFFSET+159),
  ('hockey','КХЛ','КХЛ_СКА_ЦСК','СКА','ЦСКА', MIN_OFFSET+159),
  ('football','Италия. Серия A','МАТ_РОМ_ЛАЦ','Рома','Лацио', MIN_OFFSET+160),
  ('hockey','КХЛ','КХЛ_МЕТ_АВА','Металлург Мг','Авангард', MIN_OFFSET+160),
  ('football','Лига чемпионов УЕФА','ЛИГ_АРС_БОР','Арсенал','Боруссия', MIN_OFFSET+161),
  ('basket','NBA','НБА_ГОЛ_ФИН','Голден Стэйт','Финикс', MIN_OFFSET+162),
  ('football','Лига чемпионов УЕФА','ЛИГ_БАР_ПСЖ','Барселона','ПСЖ', MIN_OFFSET+163),
  ('basket','NBA','НБА_ДАЛ_ДЕН','Даллас','Денвер', MIN_OFFSET+163),
]

result = []
for sport, league, mid_base, t1, t2, h in raw:
    dt = (now + datetime.timedelta(hours=h)).replace(minute=0, second=0, microsecond=0)
    time_str = dt.strftime('%H%M')
    mid = f'{mid_base}_{time_str}'
    odds = rand_odds()
    result.append({
        'sport': sport, 'league': league, 'id': mid,
        'date': fmt_date(dt), 'time': dt.strftime('%H:%M'),
        'team1': t1, 'team2': t2, **odds
    })

data = {'last_update': now.strftime('%Y-%m-%d %H:%M:%S'), 'matches': result}
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'matches.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'OK: {len(result)} matches saved')
print(f'Last update: {data["last_update"]}')
print(f'Sample: {result[0]["team1"]} vs {result[0]["team2"]} - {result[0]["date"]} {result[0]["time"]}')
print(f'Hockey count: {sum(1 for m in result if m["sport"]=="hockey")}')
print(f'Basket count: {sum(1 for m in result if m["sport"]=="basket")}')
print(f'Football count: {sum(1 for m in result if m["sport"]=="football")}')
print(f'Esports count: {sum(1 for m in result if m["sport"]=="esports")}')
