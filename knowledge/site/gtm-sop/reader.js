// On phones, keep the complete directory available without pushing the file below it.
const directory = document.querySelector('.directory');
if (directory && window.matchMedia('(max-width: 760px)').matches) directory.open = false;
