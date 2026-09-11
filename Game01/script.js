const COLS = 10;
const ROWS = 20;
const BLOCK_SIZE = 30;
const PREVIEW_SIZE = 24;
const COLORS = {
  I: '#4de1e1',
  J: '#5684ff',
  L: '#ff9f43',
  O: '#f8d34f',
  S: '#74e36a',
  T: '#bd70ff',
  Z: '#ff4f9a'
};
const SHAPES = {
  I: [[1, 1, 1, 1]],
  J: [[1, 0, 0], [1, 1, 1]],
  L: [[0, 0, 1], [1, 1, 1]],
  O: [[1, 1], [1, 1]],
  S: [[0, 1, 1], [1, 1, 0]],
  T: [[0, 1, 0], [1, 1, 1]],
  Z: [[1, 1, 0], [0, 1, 1]]
};

const canvas = document.getElementById('gameCanvas');
const context = canvas.getContext('2d');
const nextCanvas = document.getElementById('nextCanvas');
const nextContext = nextCanvas.getContext('2d');
const scoreElement = document.getElementById('score');
const highScoreElement = document.getElementById('highScore');
const levelElement = document.getElementById('level');
const linesElement = document.getElementById('lines');
const overlay = document.getElementById('gameOverlay');
const overlayKicker = document.getElementById('overlayKicker');
const overlayTitle = document.getElementById('overlayTitle');
const startButton = document.getElementById('startButton');
const pauseButton = document.getElementById('pauseButton');

let board;
let currentPiece;
let nextPiece;
let score = 0;
let highScore = Number(localStorage.getItem('neon-tetris-high-score') || 0);
let lines = 0;
let level = 1;
let dropCounter = 0;
let lastTime = 0;
let dropInterval = 900;
let animationId;
let gameStarted = false;
let paused = false;

function createBoard() {
  return Array.from({ length: ROWS }, () => Array(COLS).fill(0));
}

function randomPiece() {
  const types = Object.keys(SHAPES);
  const type = types[Math.floor(Math.random() * types.length)];
  return { type, matrix: SHAPES[type].map((row) => [...row]), x: 0, y: 0 };
}

function resetPiecePosition(piece) {
  piece.x = Math.floor((COLS - piece.matrix[0].length) / 2);
  piece.y = 0;
}

function startGame() {
  board = createBoard();
  score = 0;
  lines = 0;
  level = 1;
  dropInterval = 900;
  dropCounter = 0;
  currentPiece = randomPiece();
  nextPiece = randomPiece();
  resetPiecePosition(currentPiece);
  gameStarted = true;
  paused = false;
  overlay.classList.add('hidden');
  pauseButton.textContent = 'Ⅱ';
  updateStats();
  drawNextPiece();
  cancelAnimationFrame(animationId);
  lastTime = performance.now();
  animationId = requestAnimationFrame(update);
}

function update(time = 0) {
  if (!gameStarted) return;
  const delta = time - lastTime;
  lastTime = time;
  if (!paused) {
    dropCounter += delta;
    if (dropCounter > dropInterval) dropPiece();
    draw();
  }
  animationId = requestAnimationFrame(update);
}

function draw() {
  context.clearRect(0, 0, canvas.width, canvas.height);
  drawBoard();
  if (currentPiece) drawMatrix(currentPiece.matrix, currentPiece.x, currentPiece.y, context, BLOCK_SIZE, currentPiece.type);
}

function drawBoard() {
  board.forEach((row, y) => row.forEach((type, x) => {
    if (type) drawCell(context, x, y, COLORS[type], BLOCK_SIZE);
  }));
}

function drawMatrix(matrix, offsetX, offsetY, targetContext, size, type, alpha = 1) {
  targetContext.globalAlpha = alpha;
  matrix.forEach((row, y) => row.forEach((value, x) => {
    if (value) drawCell(targetContext, x + offsetX, y + offsetY, COLORS[type], size);
  }));
  targetContext.globalAlpha = 1;
}

function drawCell(targetContext, x, y, color, size) {
  const gap = Math.max(2, size * 0.08);
  const left = x * size + gap;
  const top = y * size + gap;
  targetContext.fillStyle = color;
  targetContext.fillRect(left, top, size - gap * 2, size - gap * 2);
  targetContext.fillStyle = 'rgba(255, 255, 255, 0.2)';
  targetContext.fillRect(left, top, size - gap * 2, Math.max(2, size * 0.1));
  targetContext.fillStyle = 'rgba(0, 0, 0, 0.16)';
  targetContext.fillRect(left, top + size - gap * 2 - Math.max(2, size * 0.1), size - gap * 2, Math.max(2, size * 0.1));
}

function drawNextPiece() {
  nextContext.clearRect(0, 0, nextCanvas.width, nextCanvas.height);
  const offsetX = (6 - nextPiece.matrix[0].length) / 2;
  const offsetY = (6 - nextPiece.matrix.length) / 2;
  drawMatrix(nextPiece.matrix, offsetX, offsetY, nextContext, PREVIEW_SIZE, nextPiece.type);
}

function collides(piece) {
  return piece.matrix.some((row, y) => row.some((value, x) => {
    if (!value) return false;
    const boardX = x + piece.x;
    const boardY = y + piece.y;
    return boardX < 0 || boardX >= COLS || boardY >= ROWS || (boardY >= 0 && board[boardY][boardX]);
  }));
}

function mergePiece() {
  currentPiece.matrix.forEach((row, y) => row.forEach((value, x) => {
    if (value && currentPiece.y + y >= 0) board[currentPiece.y + y][currentPiece.x + x] = currentPiece.type;
  }));
}

function dropPiece() {
  currentPiece.y += 1;
  if (collides(currentPiece)) {
    currentPiece.y -= 1;
    mergePiece();
    clearLines();
    spawnNextPiece();
  }
  dropCounter = 0;
}

function hardDrop() {
  let distance = 0;
  while (!collides(currentPiece)) {
    currentPiece.y += 1;
    distance += 1;
  }
  currentPiece.y -= 1;
  score += Math.max(0, distance - 1) * 2;
  mergePiece();
  clearLines();
  spawnNextPiece();
  dropCounter = 0;
  updateStats();
}

function movePiece(direction) {
  currentPiece.x += direction;
  if (collides(currentPiece)) currentPiece.x -= direction;
}

function rotatePiece() {
  const rotated = currentPiece.matrix[0].map((_, index) => currentPiece.matrix.map((row) => row[index]).reverse());
  const originalX = currentPiece.x;
  currentPiece.matrix = rotated;
  let offset = 0;
  while (collides(currentPiece)) {
    offset = offset > 0 ? -offset : -offset + 1;
    currentPiece.x += offset;
    if (Math.abs(offset) > currentPiece.matrix[0].length) {
      currentPiece.matrix = currentPiece.matrix.map((row) => [...row]).reverse().map((row) => row.reverse());
      currentPiece.x = originalX;
      return;
    }
  }
}

function clearLines() {
  let cleared = 0;
  board = board.filter((row) => {
    if (row.every(Boolean)) {
      cleared += 1;
      return false;
    }
    return true;
  });
  while (board.length < ROWS) board.unshift(Array(COLS).fill(0));
  if (cleared) {
    const points = [0, 100, 300, 500, 800][cleared] * level;
    score += points;
    lines += cleared;
    level = Math.floor(lines / 10) + 1;
    dropInterval = Math.max(100, 900 - (level - 1) * 70);
    updateStats();
  }
}

function spawnNextPiece() {
  currentPiece = nextPiece;
  nextPiece = randomPiece();
  resetPiecePosition(currentPiece);
  drawNextPiece();
  if (collides(currentPiece)) endGame();
}

function endGame() {
  gameStarted = false;
  paused = false;
  if (score > highScore) {
    highScore = score;
    localStorage.setItem('neon-tetris-high-score', String(highScore));
  }
  updateStats();
  overlayKicker.textContent = 'GAME OVER';
  overlayTitle.textContent = `${score.toLocaleString()} POINTS`;
  startButton.textContent = '다시 시작';
  overlay.classList.remove('hidden');
  cancelAnimationFrame(animationId);
}

function togglePause() {
  if (!gameStarted) return;
  paused = !paused;
  pauseButton.textContent = paused ? '▶' : 'Ⅱ';
  overlayKicker.textContent = 'PAUSED';
  overlayTitle.textContent = '잠시 멈춤';
  startButton.textContent = '계속하기';
  overlay.classList.toggle('hidden', !paused);
}

function updateStats() {
  scoreElement.textContent = score.toLocaleString();
  highScoreElement.textContent = highScore.toLocaleString();
  levelElement.textContent = level;
  linesElement.textContent = lines;
}

function handleAction(action) {
  if (!gameStarted || paused) return;
  if (action === 'left') movePiece(-1);
  if (action === 'right') movePiece(1);
  if (action === 'rotate') rotatePiece();
  if (action === 'down') { dropPiece(); score += 1; updateStats(); }
  if (action === 'drop') hardDrop();
  draw();
}

startButton.addEventListener('click', () => {
  if (paused) togglePause();
  else startGame();
});
pauseButton.addEventListener('click', togglePause);
document.addEventListener('keydown', (event) => {
  const actions = { ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'rotate', ArrowDown: 'down', ' ': 'drop' };
  if (event.key.toLowerCase() === 'p') togglePause();
  if (actions[event.key]) {
    event.preventDefault();
    handleAction(actions[event.key]);
  }
});
document.querySelectorAll('[data-action]').forEach((button) => {
  button.addEventListener('click', () => handleAction(button.dataset.action));
});

board = createBoard();
highScoreElement.textContent = highScore.toLocaleString();
context.fillStyle = '#0d1426';
context.fillRect(0, 0, canvas.width, canvas.height);
