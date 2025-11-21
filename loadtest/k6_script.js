/**
 * =============================================================================
 * K6 Load Test Script - Aplicación de Señas
 * =============================================================================
 * 
 * Simula N usuarios concurrentes completando ejercicios y navegando la app.
 * 
 * Escenarios:
 * - Smoke test: 1 usuario por 1 minuto
 * - Load test: Rampa de 1 a 100 usuarios en 5 minutos
 * - Stress test: Rampa de 1 a 200 usuarios, luego descenso
 * - Spike test: Subida abrupta a 500 usuarios
 * 
 * Métricas monitoreadas:
 * - Response time (p95, p99)
 * - Error rate
 * - Requests per second
 * - Custom: XP ganado, ejercicios completados, levelUps
 * 
 * =============================================================================
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';

// =============================================================================
// Configuración
// =============================================================================

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const SCENARIO = __ENV.SCENARIO || 'load'; // smoke, load, stress, spike

// =============================================================================
// Métricas Personalizadas
// =============================================================================

const errorRate = new Rate('errors');
const exerciseCompletionTime = new Trend('exercise_completion_time');
const xpEarned = new Counter('xp_earned');
const exercisesCompleted = new Counter('exercises_completed');
const levelUps = new Counter('level_ups');
const livesLost = new Counter('lives_lost');
const apiLoginDuration = new Trend('api_login_duration');
const apiExerciseDuration = new Trend('api_exercise_duration');

// =============================================================================
// Configuración de Escenarios
// =============================================================================

const scenarios = {
  smoke: {
    executor: 'constant-vus',
    vus: 1,
    duration: '1m',
  },
  
  load: {
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '2m', target: 20 },   // Ramp-up a 20 usuarios
      { duration: '5m', target: 20 },   // Stay en 20
      { duration: '2m', target: 50 },   // Ramp-up a 50
      { duration: '5m', target: 50 },   // Stay en 50
      { duration: '2m', target: 100 },  // Ramp-up a 100
      { duration: '5m', target: 100 },  // Stay en 100
      { duration: '2m', target: 0 },    // Ramp-down
    ],
    gracefulRampDown: '30s',
  },
  
  stress: {
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '2m', target: 50 },
      { duration: '5m', target: 100 },
      { duration: '5m', target: 200 },
      { duration: '5m', target: 300 },  // Stress point
      { duration: '2m', target: 0 },
    ],
  },
  
  spike: {
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '10s', target: 500 }, // Spike rápido
      { duration: '1m', target: 500 },
      { duration: '10s', target: 0 },
    ],
  },
  
  soak: {
    executor: 'constant-vus',
    vus: 50,
    duration: '30m', // Test de duración prolongada
  }
};

export const options = {
  scenarios: {
    main: scenarios[SCENARIO],
  },
  
  thresholds: {
    // Thresholds generales
    'http_req_duration': ['p(95)<500', 'p(99)<1000'], // 95% < 500ms, 99% < 1s
    'http_req_failed': ['rate<0.01'],                  // Error rate < 1%
    'errors': ['rate<0.01'],
    
    // Thresholds por endpoint
    'http_req_duration{endpoint:login}': ['p(95)<300'],
    'http_req_duration{endpoint:exercise}': ['p(95)<600'],
    'http_req_duration{endpoint:submit}': ['p(95)<400'],
    
    // Thresholds custom
    'exercise_completion_time': ['p(95)<2000'], // Ejercicio completo < 2s
  },
  
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
};

// =============================================================================
// Datos de Test
// =============================================================================

const users = new SharedArray('users', function () {
  const userList = [];
  for (let i = 1; i <= 1000; i++) {
    userList.push({
      email: `loadtest.user${i}@example.com`,
      password: 'LoadTest123!',
      username: `loadtest_user_${i}`
    });
  }
  return userList;
});

const exerciseTypes = ['test', 'camera'];
const difficulties = ['beginner', 'intermediate', 'advanced'];

// =============================================================================
// Funciones de Utilidad
// =============================================================================

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randomElement(array) {
  return array[Math.floor(Math.random() * array.length)];
}

function getAuthHeaders(token) {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };
}

// =============================================================================
// Funciones de API
// =============================================================================

function registerUser(userData) {
  const payload = JSON.stringify(userData);
  
  const response = http.post(
    `${BASE_URL}/auth/register`,
    payload,
    { headers: { 'Content-Type': 'application/json' } }
  );
  
  return check(response, {
    'registration successful': (r) => r.status === 201,
    'has user_id': (r) => JSON.parse(r.body).user_id !== undefined,
  });
}

function loginUser(email, password) {
  const startTime = Date.now();
  
  const payload = JSON.stringify({ email, password });
  
  const response = http.post(
    `${BASE_URL}/auth/login`,
    payload,
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { endpoint: 'login' },
    }
  );
  
  const success = check(response, {
    'login successful': (r) => r.status === 200,
    'has access_token': (r) => JSON.parse(r.body).access_token !== undefined,
    'has id_token': (r) => JSON.parse(r.body).id_token !== undefined,
  });
  
  errorRate.add(!success);
  
  if (success) {
    const duration = Date.now() - startTime;
    apiLoginDuration.add(duration);
    
    const body = JSON.parse(response.body);
    return body.id_token;
  }
  
  return null;
}

function getUserProfile(token) {
  const response = http.get(
    `${BASE_URL}/users/me`,
    {
      headers: getAuthHeaders(token),
      tags: { endpoint: 'profile' },
    }
  );
  
  const success = check(response, {
    'profile retrieved': (r) => r.status === 200,
    'has lives': (r) => JSON.parse(r.body).lives !== undefined,
    'has xp': (r) => JSON.parse(r.body).xp !== undefined,
  });
  
  errorRate.add(!success);
  
  return success ? JSON.parse(response.body) : null;
}

function getNextExercise(token, type = 'test') {
  const response = http.get(
    `${BASE_URL}/exercises/next?type=${type}`,
    {
      headers: getAuthHeaders(token),
      tags: { endpoint: 'exercise' },
    }
  );
  
  const success = check(response, {
    'exercise retrieved': (r) => r.status === 200,
    'has exercise id': (r) => JSON.parse(r.body).id !== undefined,
  });
  
  errorRate.add(!success);
  
  return success ? JSON.parse(response.body) : null;
}

function submitExercise(token, exerciseId, isCorrect = true, timeSpent = null) {
  const startTime = Date.now();
  const actualTimeSpent = timeSpent || randomInt(15, 45);
  
  const payload = JSON.stringify({
    exercise_id: exerciseId,
    answer: isCorrect ? 'correct_answer' : 'wrong_answer',
    time_spent: actualTimeSpent,
  });
  
  const response = http.post(
    `${BASE_URL}/exercises/submit`,
    payload,
    {
      headers: getAuthHeaders(token),
      tags: { endpoint: 'submit' },
    }
  );
  
  const success = check(response, {
    'submission successful': (r) => r.status === 200,
    'has xp_earned': (r) => JSON.parse(r.body).xp_earned !== undefined,
  });
  
  errorRate.add(!success);
  
  if (success) {
    const duration = Date.now() - startTime;
    apiExerciseDuration.add(duration);
    exerciseCompletionTime.add(actualTimeSpent * 1000);
    
    const result = JSON.parse(response.body);
    
    // Métricas custom
    xpEarned.add(result.xp_earned || 0);
    exercisesCompleted.add(1);
    
    if (result.level_up) {
      levelUps.add(1);
    }
    
    if (result.life_lost) {
      livesLost.add(1);
    }
    
    return result;
  }
  
  return null;
}

function getWeeklyStats(token) {
  const response = http.get(
    `${BASE_URL}/stats/weekly`,
    {
      headers: getAuthHeaders(token),
      tags: { endpoint: 'stats' },
    }
  );
  
  check(response, {
    'stats retrieved': (r) => r.status === 200,
  });
}

// =============================================================================
// Escenario Principal
// =============================================================================

export default function () {
  // Seleccionar usuario aleatorio
  const user = users[__VU % users.length];
  
  group('User Authentication', function () {
    const token = loginUser(user.email, user.password);
    
    if (!token) {
      console.error(`Login failed for ${user.email}`);
      return;
    }
    
    sleep(randomInt(1, 3));
    
    group('User Profile', function () {
      const profile = getUserProfile(token);
      
      if (!profile) {
        console.error('Failed to get profile');
        return;
      }
      
      sleep(randomInt(1, 2));
      
      // Simular sesión de práctica
      group('Practice Session', function () {
        const exercisesToComplete = randomInt(3, 7);
        
        for (let i = 0; i < exercisesToComplete; i++) {
          // Verificar si tenemos vidas
          const currentProfile = getUserProfile(token);
          
          if (currentProfile && currentProfile.lives <= 0) {
            console.log('No lives remaining, ending session');
            break;
          }
          
          // Obtener ejercicio
          const exerciseType = randomElement(exerciseTypes);
          const exercise = getNextExercise(token, exerciseType);
          
          if (!exercise) {
            console.error('Failed to get exercise');
            break;
          }
          
          // Simular tiempo pensando
          sleep(randomInt(5, 10));
          
          // Completar ejercicio (85% de probabilidad de correcto)
          const isCorrect = Math.random() < 0.85;
          const result = submitExercise(token, exercise.id, isCorrect);
          
          if (!result) {
            console.error('Failed to submit exercise');
            break;
          }
          
          // Pequeña pausa entre ejercicios
          sleep(randomInt(2, 5));
        }
      });
      
      // Obtener estadísticas al final
      sleep(randomInt(1, 2));
      getWeeklyStats(token);
    });
  });
  
  // Pausa antes de la siguiente iteración
  sleep(randomInt(5, 15));
}

// =============================================================================
// Setup y Teardown
// =============================================================================

export function setup() {
  console.log(`
    ╔══════════════════════════════════════════════════════════════╗
    ║  K6 Load Test - Aplicación de Señas                         ║
    ║  Scenario: ${SCENARIO.padEnd(50)}║
    ║  Base URL: ${BASE_URL.padEnd(50)}║
    ╚══════════════════════════════════════════════════════════════╝
  `);
  
  // Verificar que el servidor está disponible
  const response = http.get(`${BASE_URL}/health`);
  
  if (response.status !== 200) {
    throw new Error('Server is not available');
  }
  
  console.log('✅ Server is healthy and ready for load test');
  
  return { timestamp: new Date().toISOString() };
}

export function teardown(data) {
  console.log(`
    ╔══════════════════════════════════════════════════════════════╗
    ║  Load Test Completed                                         ║
    ║  Started: ${data.timestamp.padEnd(49)}║
    ║  Ended:   ${new Date().toISOString().padEnd(49)}║
    ╚══════════════════════════════════════════════════════════════╝
  `);
}

// =============================================================================
// Handlers de Threshold Violations
// =============================================================================

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: '  ', enableColors: true }),
    'summary.json': JSON.stringify(data),
    'summary.html': htmlReport(data),
  };
}

function textSummary(data, options) {
  const indent = options.indent || '';
  const enableColors = options.enableColors || false;
  
  let summary = '\n';
  summary += `${indent}╔══════════════════════════════════════════════════════════════╗\n`;
  summary += `${indent}║  📊 LOAD TEST SUMMARY                                        ║\n`;
  summary += `${indent}╚══════════════════════════════════════════════════════════════╝\n\n`;
  
  // Métricas generales
  const metrics = data.metrics;
  
  summary += `${indent}🎯 Performance Metrics:\n`;
  summary += `${indent}  ├─ Requests:           ${metrics.http_reqs.values.count}\n`;
  summary += `${indent}  ├─ Request duration:   p(95)=${metrics.http_req_duration.values['p(95)'].toFixed(2)}ms\n`;
  summary += `${indent}  ├─ Failed requests:    ${(metrics.http_req_failed.values.rate * 100).toFixed(2)}%\n`;
  summary += `${indent}  └─ Requests/sec:       ${metrics.http_reqs.values.rate.toFixed(2)}\n\n`;
  
  // Métricas custom
  summary += `${indent}📈 Application Metrics:\n`;
  summary += `${indent}  ├─ Exercises completed: ${metrics.exercises_completed.values.count}\n`;
  summary += `${indent}  ├─ Total XP earned:     ${metrics.xp_earned.values.count}\n`;
  summary += `${indent}  ├─ Level ups:           ${metrics.level_ups.values.count}\n`;
  summary += `${indent}  └─ Lives lost:          ${metrics.lives_lost.values.count}\n\n`;
  
  // Thresholds
  summary += `${indent}✅ Thresholds:\n`;
  Object.keys(data.thresholds).forEach(name => {
    const threshold = data.thresholds[name];
    const passed = Object.values(threshold).every(t => t.ok);
    const icon = passed ? '✅' : '❌';
    summary += `${indent}  ${icon} ${name}\n`;
  });
  
  return summary;
}

function htmlReport(data) {
  // Generar reporte HTML básico
  return `
    <!DOCTYPE html>
    <html>
    <head>
      <title>K6 Load Test Report</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        .pass { color: green; }
        .fail { color: red; }
      </style>
    </head>
    <body>
      <h1>Load Test Summary</h1>
      <h2>Metrics</h2>
      <table>
        <tr>
          <th>Metric</th>
          <th>Value</th>
        </tr>
        <tr>
          <td>Total Requests</td>
          <td>${data.metrics.http_reqs.values.count}</td>
        </tr>
        <tr>
          <td>Failed Requests</td>
          <td class="${data.metrics.http_req_failed.values.rate < 0.01 ? 'pass' : 'fail'}">
            ${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%
          </td>
        </tr>
        <tr>
          <td>P95 Response Time</td>
          <td>${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms</td>
        </tr>
        <tr>
          <td>Exercises Completed</td>
          <td>${data.metrics.exercises_completed.values.count}</td>
        </tr>
        <tr>
          <td>XP Earned</td>
          <td>${data.metrics.xp_earned.values.count}</td>
        </tr>
      </table>
    </body>
    </html>
  `;
}
