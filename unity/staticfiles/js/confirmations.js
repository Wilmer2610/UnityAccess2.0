document.addEventListener('DOMContentLoaded', () => {
  // Confirmaciones para formularios (crear/editar/eliminar)
  document.querySelectorAll('form.js-confirm').forEach((form) => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const title = form.dataset.confirmTitle || 'Confirmar acción';
      const text = form.dataset.confirmText || '¿Deseas continuar?';
      const icon = form.dataset.confirmIcon || 'question';
      Swal.fire({
        title,
        text,
        icon,
        showCancelButton: true,
        confirmButtonText: 'Sí, continuar',
        cancelButtonText: 'Cancelar',
        reverseButtons: true
      }).then((result) => {
        if (result.isConfirmed) {
          form.submit();
        }
      });
    });
  });

  // Confirmaciones para enlaces de eliminación (soporta ambas clases)
  document.querySelectorAll('a.js-delete-link, a.js-confirm-link').forEach((link) => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const href = link.getAttribute('href');
      const title = link.dataset.confirmTitle || 'Eliminar';
      const text = link.dataset.confirmText || '¿Deseas continuar?';
      const icon = link.dataset.confirmIcon || 'warning';
      Swal.fire({
        title,
        text,
        icon,
        showCancelButton: true,
        confirmButtonColor: '#d33',
        confirmButtonText: 'Sí, eliminar',
        cancelButtonText: 'Cancelar',
        reverseButtons: true
      }).then((result) => {
        if (result.isConfirmed) {
          window.location.href = href;
        }
      });
    });
  });

  // Mostrar mensajes de Django como toasts
  const container = document.getElementById('django-messages');
  if (container) {
    container.querySelectorAll('div[data-level]').forEach((el, idx) => {
      const level = el.getAttribute('data-level') || 'info';
      const iconMap = { success: 'success', error: 'error', warning: 'warning', info: 'info' };
      const icon = iconMap[level] || 'info';
      setTimeout(() => {
        Swal.fire({
          toast: true,
          position: 'top-end',
          icon,
          title: el.textContent.trim(),
          showConfirmButton: false,
          timer: 3000,
          timerProgressBar: true
        });
      }, idx * 200);
    });
  }
});