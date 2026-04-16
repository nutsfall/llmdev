window.onload = function() {
  const chatBox = document.getElementById('chat-box');
  const form = document.getElementById('chat-form');
  const textarea = document.getElementById('user-input');
  const submitButton = document.getElementById('submit-button');

  if (!chatBox || !form || !textarea || !submitButton) {
    return;
  }

  // チャットボックスのスクロールを一番下に設定
  chatBox.scrollTop = chatBox.scrollHeight;

  // Ctrl + Enter / (macOS) Command + Enterでフォームを送信
  const isMac = /Mac|iPhone|iPad|iPod/.test(navigator.platform);

  textarea.addEventListener('keydown', function(event) {
    const ctrlEnter = event.ctrlKey && event.key === 'Enter';
    const commandEnterOnMac = isMac && event.metaKey && event.key === 'Enter';

    if (ctrlEnter || commandEnterOnMac) {
      event.preventDefault();
      if (submitButton.disabled) {
        return;
      }
      if (form.requestSubmit) {
        form.requestSubmit();
      } else {
        form.submit();
      }
    }
  });

  form.addEventListener('submit', function() {
    submitButton.disabled = true;
    submitButton.textContent = '送信中...';
    textarea.readOnly = true;
    textarea.classList.add('is-submitting');
    textarea.setAttribute('aria-busy', 'true');
  });
};