/**
 * A tiny demo module for the sub-pipeline example.
 */

function add(a, b) {
  return a + b;
}

function greet(name) {
  return `Hello, ${name || "world"}!`;
}

module.exports = { add, greet };
