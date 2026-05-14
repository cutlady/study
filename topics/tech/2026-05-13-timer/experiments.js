// 实验1：基本用法
console.log('=== 实验1：基本用法 ===');

setTimeout(() => console.log('setTimeout: 1秒后执行'), 1000);
const s1 = setInterval(() => console.log('setInterval: 每1秒执行一次'), 1000);
const s2 = setInterval(() => console.log('setInterval: 每1秒执行一次'), 1000);

console.log(s1,s2)

// 5秒后清理 interval，否则永远不停
const intervalId = setInterval(() => {}, 1000);
setTimeout(() => {
  clearInterval(intervalId);
  console.log('已清理 interval');
}, 5000);


// 实验2：setTimeout 实现 setInterval（递归模式）
console.log('\n=== 实验2：递归 setTimeout 模拟 interval ===');

let count = 0;
function repeatedTask() {
  console.log(`递归 setTimeout 执行第 ${++count} 次`);
  if (count < 3) {
    setTimeout(repeatedTask, 1000);
  }
}
setTimeout(repeatedTask, 1000);


// 实验3：累积误差对比
console.log('\n=== 实验3：累积误差（模拟主线程阻塞） ===');

// setInterval 版本
let start1 = Date.now();
let ticks1 = 0;
const si = setInterval(() => {
  ticks1++;
  const elapsed = Date.now() - start1;
  console.log(`setInterval  tick=${ticks1}  实际间隔=${elapsed}ms  误差=${elapsed - ticks1 * 1000}ms`);

  // 模拟主线程阻塞 300ms
  const waste = Date.now();
  while (Date.now() - waste < 300) {} // 阻塞

  if (ticks1 >= 5) clearInterval(si);
}, 1000);

// 递归 setTimeout 版本
let start2 = Date.now();
let ticks2 = 0;
function recursiveTimeout() {
  ticks2++;
  const elapsed = Date.now() - start2;
  console.log(`递归setTimeout tick=${ticks2}  实际间隔=${elapsed}ms  误差=${elapsed - ticks2 * 1300}ms`);

  // 同样模拟阻塞 300ms
  const waste = Date.now();
  while (Date.now() - waste < 300) {}

  if (ticks2 < 5) {
    setTimeout(recursiveTimeout, 1000);
  }
}
setTimeout(recursiveTimeout, 1000);
