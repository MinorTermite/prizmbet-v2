// Netlify serverless function: получает данные из Google Sheets CSV
// Вызов: GET /.netlify/functions/update-matches

const SHEET_ID = process.env.SHEET_ID || '1QkVj51WMKSd6-LU4vZK3dYPk6QLQIO014ydpACtThNk';
const GID = process.env.SHEET_GID || '0';
const CSV_URL = `https://docs.google.com/spreadsheets/d/${SHEET_ID}/export?format=csv&gid=${GID}`;

// Маппинг спортов (ключ — начало названия лиги)
const SPORT_MAP = {
  // FOOTBALL
  'Лига чемпионов УЕФА': 'football', 'Лига Европы УЕФА': 'football',
  'Лига конференций УЕФА': 'football', 'УЕФА': 'football', 'UEFA': 'football',
  'Англия. Премьер-лига': 'football', 'Англия. Чемпионшип': 'football',
  'Англия. Кубок': 'football', 'Англия. Кубок Лиги': 'football',
  'Испания. Ла Лига': 'football', 'Испания. Сегунда': 'football',
  'Испания. Кубок Короля': 'football',
  'Германия. Бундеслига': 'football', 'Германия. 2. Бундеслига': 'football',
  'Германия. Кубок': 'football',
  'Италия. Серия A': 'football', 'Италия. Серия B': 'football',
  'Итальянский. Кубок': 'football',
  'Франция. Лига 1': 'football', 'Франция. Лига 2': 'football',
  'Россия. Премьер-лига': 'football', 'Россия. ФНЛ': 'football',
  'Россия. Кубок': 'football',
  'Нидерланды. Эредивизие': 'football', 'Португалия. Примейра Лига': 'football',
  'Турция. Суперлига': 'football', 'Шотландия. Премьершип': 'football',
  'Бельгия. Про Лига': 'football', 'Бразилия. Серия A': 'football',
  'Аргентина. Примера Дивисьон': 'football',
  'США. MLS': 'football', 'MLS': 'football', 'Мексика. Лига MX': 'football',
  'КОНМЕБОЛ. Копа Либертадорес': 'football', 'КОНКАКАФ': 'football',
  'Саудовская Аравия. Про Лига': 'football',
  'Япония. Джей-Лига': 'football', 'Южная Корея. К-Лига': 'football',
  'Греция. Суперлига': 'football', 'Украина. Премьер-лига': 'football',
  'Польша. Экстракласа': 'football', 'Австрия. Бундеслига': 'football',
  'Швейцария. Суперлига': 'football', 'Дания. Суперлига': 'football',
  'Норвегия. Элитесерия': 'football', 'Швеция. Алльсвенскан': 'football',
  // HOCKEY
  'КХЛ': 'hockey', 'НХЛ': 'hockey', 'NHL': 'hockey',
  'ВХЛ': 'hockey', 'МХЛ': 'hockey', 'AHL': 'hockey', 'ECHL': 'hockey',
  'Швеция. SHL': 'hockey', 'Финляндия. Liiga': 'hockey',
  'Чехия. Extraliga': 'hockey', 'Германия. DEL': 'hockey',
  'Швейцария. National League': 'hockey', 'Беларусь. Экстралига': 'hockey',
  'Казахстан. ЧРК': 'hockey', 'Австрия. ICEHL': 'hockey',
  // BASKETBALL
  'NBA': 'basket', 'НБА': 'basket', 'Евролига': 'basket',
  'EuroLeague': 'basket', 'EuroCup': 'basket',
  'Единая лига ВТБ': 'basket', 'Испания. ACB': 'basket',
  'Турция. BSL': 'basket', 'Германия. BBL': 'basket',
  'Греция. HEBA A1': 'basket', 'Австралия. NBL': 'basket',
  'Китай. CBA': 'basket', 'ФИБА': 'basket', 'FIBA': 'basket',
  // ESPORTS
  'CS2': 'esports', 'Counter-Strike': 'esports', 'Dota 2': 'esports',
  'Valorant': 'esports', 'League of Legends': 'esports', 'LoL': 'esports',
  'Rocket League': 'esports', 'RLCS': 'esports', 'PUBG': 'esports',
  'Apex Legends': 'esports', 'Rainbow Six': 'esports', 'Overwatch': 'esports',
  // TENNIS
  'ATP': 'tennis', 'WTA': 'tennis', 'ITF': 'tennis', 'Теннис': 'tennis',
  // VOLLEYBALL
  'CEV': 'volleyball', 'ВНЛ': 'volleyball', 'VNL': 'volleyball',
  'Россия. Суперлига': 'volleyball', 'Польша. PlusLiga': 'volleyball',
  'Италия. SuperLega': 'volleyball', 'Волейбол': 'volleyball',
  // MMA
  'UFC': 'mma', 'Bellator': 'mma', 'ONE Championship': 'mma',
  'ONE FC': 'mma', 'ACB MMA': 'mma', 'PFL': 'mma', 'M-1': 'mma',
};

function detectSport(league) {
  for (const [key, sport] of Object.entries(SPORT_MAP)) {
    if (league.startsWith(key)) return sport;
  }
  const ll = league.toLowerCase();
  if (/футбол|лига|премьер|кубок|уефа|серия|бундес|ла лига|копа|mls/.test(ll)) return 'football';
  if (/хоккей|кхл|нхл|hockey|nhl|ahl|shl|liiga|del/.test(ll)) return 'hockey';
  if (/баскет|nba|евролига|basketball|vtb|acb/.test(ll)) return 'basket';
  if (/dota|cs2|counter-strike|valorant|esports|rlcs|pubg|apex/.test(ll)) return 'esports';
  if (/теннис|atp|wta|itf|уимблдон|ролан/.test(ll)) return 'tennis';
  if (/волейбол|volleyball|cev|vnl|plusliga|superlega/.test(ll)) return 'volleyball';
  if (/ufc|bellator|mma|one championship|pfl/.test(ll)) return 'mma';
  return 'football';
}

function parseCSV(text) {
  const lines = text.trim().split('\n');
  const matches = [];

  // Пропускаем заголовок
  for (let i = 1; i < lines.length; i++) {
    const row = parseCSVLine(lines[i]);
    if (row.length < 12) continue;

    const league = (row[0] || '').trim();
    const id = (row[1] || '').trim();
    const date = (row[2] || '').trim();
    const time = (row[3] || '').trim();
    let team1 = (row[4] || '').trim();
    let team2 = (row[5] || '').trim();

    if (!league || !team1 || !team2) continue;

    // Очистка команд от встроенных дат (кириллица: "17 фев 20:45", "1 янв 10:00")
    const dateTimeRx = /\d{1,2}\s+[а-яёА-ЯЁa-zA-Z]{2,4}\s+\d{1,2}:\d{2}/g;
    team1 = team1.replace(dateTimeRx, '').trim();
    team2 = team2.replace(dateTimeRx, '').trim();
    if (!team1 || !team2) continue;

    matches.push({
      sport: detectSport(league),
      league,
      id,
      date,
      time,
      team1,
      team2,
      p1: (row[6] || '0.00').trim(),
      x: (row[7] || '0.00').trim(),
      p2: (row[8] || '0.00').trim(),
      p1x: (row[9] || '0.00').trim(),
      p12: (row[10] || '0.00').trim(),
      px2: (row[11] || '0.00').trim(),
    });
  }

  return matches;
}

// Простой CSV парсер с поддержкой кавычек
function parseCSVLine(line) {
  const result = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"' && line[i + 1] === '"') {
        current += '"';
        i++;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        current += ch;
      }
    } else {
      if (ch === '"') {
        inQuotes = true;
      } else if (ch === ',') {
        result.push(current);
        current = '';
      } else {
        current += ch;
      }
    }
  }
  result.push(current);
  return result;
}

exports.handler = async (event) => {
  const headers = {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Cache-Control': 'public, max-age=300',
  };

  try {
    console.log('Fetching CSV from Google Sheets...');
    const response = await fetch(CSV_URL, {
      headers: { 'User-Agent': 'PRIZMBET-Netlify/1.0' },
      signal: AbortSignal.timeout(15000),
    });

    if (!response.ok) {
      throw new Error(`Google Sheets HTTP ${response.status}`);
    }

    const csvText = await response.text();
    if (!csvText.trim()) {
      throw new Error('Empty response from Google Sheets');
    }

    const matches = parseCSV(csvText);
    console.log(`Parsed ${matches.length} matches`);

    const data = {
      last_update: new Date().toISOString().replace('T', ' ').slice(0, 19),
      matches,
    };

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify(data),
    };

  } catch (error) {
    console.error('Error:', error.message);
    return {
      statusCode: 502,
      headers,
      body: JSON.stringify({
        error: 'Failed to fetch data',
        message: error.message,
        last_update: null,
        matches: [],
      }),
    };
  }
};
