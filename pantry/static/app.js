const $ = (selector) => document.querySelector(selector);
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
fetch('/health').then(r => r.json()).then(data => {
  $('#mode').textContent = data.mode === 'demo' ? 'Demo kitchen' : 'Local model kitchen';
  if (data.mode === 'demo') $('#mode-note').textContent = 'Demo mode serves one sample recipe per cuisine, scaled to your servings. Ingredient matching and retrieval use keywords. Enable Ollama for customized generation and semantic search.';
}).catch(() => { $('#mode').textContent = 'Kitchen offline'; });
document.querySelectorAll('[data-example]').forEach(button => {
  button.addEventListener('click', () => {
    $('#ingredients').value = button.dataset.example;
    $('#cuisine').value = button.dataset.cuisine;
  });
});
function render(data) {
  const result = $('#result');
  const recipe = data.recipe;
  result.replaceChildren(element('p', data.mode === 'demo' ? '02 / SAMPLE RECIPE' : '02 / YOUR RECIPE', 'eyebrow'), element('h2', recipe.title));
  const meta = element('div', undefined, 'meta');
  [recipe.cuisine, `${recipe.minutes} min`, `${recipe.servings} servings`].forEach(value => meta.append(element('span', value)));
  result.append(meta, element('h3', 'What you’ll need'));
  const ingredients = element('ul', undefined, 'ingredients');
  recipe.ingredients.forEach(item => {
    const row = element('li');
    row.append(element('span', item.name), element('span', item.quantity));
    ingredients.append(row);
  });
  result.append(ingredients);
  if (data.additional_ingredients.length) result.append(element('p', 'Also needed: ' + data.additional_ingredients.join(', '), 'notice'));
  [['Before you start', recipe.preparation], ['Let’s cook', recipe.instructions], ['Kitchen notes', recipe.tips]].forEach(([title, items]) => {
    result.append(element('h3', title));
    const list = element('ol');
    items.forEach(text => list.append(element('li', text)));
    result.append(list);
  });
  const context = element('details');
  context.append(element('summary', `Retrieved cooking notes · ${data.retrieval} search`));
  context.append(element('p', 'Reference notes supplied to generation; these are not verified citations for every recipe claim.'));
  data.context.forEach(item => {
    const section = element('div', undefined, 'context');
    section.append(element('strong', item.title), element('p', item.text), element('small', `Similarity ${item.score.toFixed(3)} · ${item.id}`));
    context.append(section);
  });
  result.append(context);
}
$('#recipe-form').addEventListener('submit', async event => {
  event.preventDefault();
  const ingredients = $('#ingredients').value.split(',').map(s => s.trim()).filter(Boolean);
  if (!ingredients.length || ingredients.length > 25 || ingredients.some(s => s.length > 60)) {
    $('#status').textContent = 'Enter 1–25 ingredients, each up to 60 characters.';
    return;
  }
  $('#generate').disabled = true;
  $('#status').textContent = 'Finding a little inspiration…';
  $('#result').setAttribute('aria-busy', 'true');
  try {
    const response = await fetch('/api/recipes', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ingredients, cuisine: $('#cuisine').value, servings: Number($('#servings').value)})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Please check your ingredients and serving count.');
    render(data);
    $('#status').textContent = data.mode === 'demo' ? 'Sample recipe ready. Enable Ollama for a custom recipe.' : 'Your recipe is ready.';
  } catch (error) { $('#status').textContent = error.message || 'Could not load a recipe. Please try again.'; }
  finally { $('#generate').disabled = false; $('#result').removeAttribute('aria-busy'); }
});
