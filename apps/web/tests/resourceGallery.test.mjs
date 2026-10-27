import assert from 'node:assert/strict'
import { test } from 'node:test'
import { cardPage, galleryCards, oldestFirst } from '../src/resourceGallery.ts'
const make=(id,meta={})=>({id,title:id,kind:'learning',meta})
test('explicit author collections become one folder and ordinary posts stay single',()=>{
  const docs=[make('one'),make('a',{author_collection_id:'author-1',author_collection_title:'某设计博主'}),make('b',{author_collection_id:'author-1'}),make('two',{source_author:'另一个博主'})]
  const rows=galleryCards(docs)
  assert.equal(rows.length,3)
  assert.equal(rows.filter(x=>x.folder).length,1)
  assert.equal(rows.find(x=>x.folder).postCount,2)
  assert.equal(rows.find(x=>x.folder).title,'某设计博主')
  assert.equal(docs.length,4)
})
test('oldest-first uses source creation sequence across years and keeps undated posts last',()=>{
  const rows=[make('new',{source_id:'6962d44c000000000a030ebd',displayed_date:'编辑于 05-22'}),make('unknown'),make('old',{source_url:'https://www.xiaohongshu.com/explore/66619783000000000e033430',displayed_date:'编辑于 10-12'}),make('dated',{published_at:'2023-01-01T00:00:00+08:00'})]
  assert.deepEqual(oldestFirst(rows).map(x=>x.id),['dated','old','new','unknown'])
  assert.equal(rows[0].id,'new')
})
test('pagination gives exactly nine and covers every item once',()=>{
  const rows=Array.from({length:28},(_,i)=>i)
  const pages=Array.from({length:4},(_,i)=>cardPage(rows,i+1))
  assert.deepEqual(pages.map(x=>x.items.length),[9,9,9,1])
  assert.deepEqual(pages.flatMap(x=>x.items),rows)
})
test('invalid or deleted final page clamps to a real page',()=>{
  assert.equal(cardPage([1,2],99).page,1)
  assert.equal(cardPage([],2).pages,1)
  for(const value of [-1,0,'bad',Infinity]) assert.equal(cardPage([1],value).page,1)
  assert.equal(cardPage(Array(10).fill(0),1.9).page,1)
})
test('pagination counts folder cards, not hidden posts',()=>{
  const rows=Array.from({length:137},(_,i)=>make('post'+i,{author_collection_id:'author-1'}))
  rows.push(...Array.from({length:20},(_,i)=>make('single'+i)))
  const page=cardPage(galleryCards(rows),3)
  assert.equal(page.total,21)
  assert.equal(page.pages,3)
  assert.equal(page.items.length,3)
})
