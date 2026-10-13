"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const {parseCSV, analyzePSMs} = require("../web/app.js");

const source = "psm_id,score,is_decoy\n" +
  "s1,10,false\ns2,9,false\ns3,8,true\ns4,7,false\n";

test("TDC+ produces expected q-values and accepts only targets", () => {
  const result = analyzePSMs(parseCSV(source), 0.5);
  assert.equal(result.accepted, 2);
  assert.equal(result.threshold, 9);
  assert.deepEqual(result.rows.map((r) => r.accepted), [true, true, false, false]);
  assert.deepEqual(result.rows.map((r) => Number(r.q_value.toFixed(6))),
    [0.5, 0.5, 0.666667, 0.666667]);
});

test("ties are independent of input order", () => {
  const a = analyzePSMs(parseCSV("psm_id,score,is_decoy\nt1,10,false\nd1,10,true\nt2,8,false"), 0.5);
  const b = analyzePSMs(parseCSV("psm_id,score,is_decoy\nd1,10,true\nt1,10,false\nt2,8,false"), 0.5);
  const values = (result) => Object.fromEntries(result.rows.map((r) => [r.psm_id, r.q_value]));
  assert.deepEqual(values(a), values(b));
});

test("zero decoys does not mean zero FDR", () => {
  const rows = Array.from({length: 20}, (_, n) => ({psm_id: "s" + n, score: String(n), is_decoy: "false"}));
  const result = analyzePSMs(rows, 0.01);
  assert.equal(result.accepted, 0);
  assert.equal(result.rows[0].q_value, 0.05);
});

test("rejects invalid scores, duplicates and formula-like IDs", () => {
  assert.throws(() => analyzePSMs(parseCSV("psm_id,score,is_decoy\ns1,NaN,true"), 0.1));
  assert.throws(() => analyzePSMs(parseCSV("psm_id,score,is_decoy\ns1,1,true\ns1,2,false"), 0.1));
  assert.throws(() => analyzePSMs(parseCSV("psm_id,score,is_decoy\n=cmd,1,true"), 0.1));
});

test("accepts BOM, CRLF, and quoted fields", () => {
  const rows = parseCSV("\uFEFFpsm_id,score,is_decoy\r\n\"s1\",\"10\",\"false\"\r\n");
  assert.equal(rows[0].psm_id, "s1");
});
