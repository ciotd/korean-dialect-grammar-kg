const search=document.getElementById('search');
const cases=[...document.querySelectorAll('.sentence')];
function filter(){let count=0;for(const el of cases){el.hidden=!el.textContent.toLowerCase().includes(search.value.trim().toLowerCase());if(!el.hidden)count++;}document.getElementById('count').textContent=`50문장 중 ${count}문장을 표시합니다. 문장을 누르면 처리 내용을 펼칠 수 있습니다.`;}
search.addEventListener('input',filter);filter();
function reveal(){const id=decodeURIComponent(location.hash.slice(1));const target=document.getElementById(id);if(!target)return;if(target.classList.contains('sentence')&&target.hidden){search.value='';filter();}for(let p=target;p;p=p.parentElement){if(p.tagName==='DETAILS')p.open=true;}target.scrollIntoView({block:'start'});}
window.addEventListener('hashchange',reveal);if(location.hash)reveal();
