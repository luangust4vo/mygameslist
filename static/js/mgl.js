/*
 * Plugins jQuery do MyGamesList.
 * - Select2: selects marcados com data-buscavel ganham busca. (Não use
 *   data-select2: o plugin guarda a instância em .data("select2") e trava.)
 * - Bootbox: links e formulários com data-confirmar pedem confirmação num modal.
 *   data-confirmar-classe troca a cor do botão (padrão: btn-danger).
 *   Links fazem POST para o próprio href; sem JavaScript, o link abre a página
 *   de confirmação do Django.
 */
$(function () {
    $('select[data-buscavel]').each(function () {
        $(this).select2({
            language: 'pt-BR',
            width: '100%',
            dropdownParent: $(this).parent(),
        });
    });

    function confirmar(elemento, aoConfirmar) {
        var $el = $(elemento);
        bootbox.confirm({
            title: $el.data('confirmar-titulo') || 'Tem certeza?',
            message: $('<p>').text($el.data('confirmar')),
            centerVertical: true,
            buttons: {
                confirm: {
                    label: $el.data('confirmar-botao') || 'Confirmar',
                    className: $el.data('confirmar-classe') || 'btn-danger',
                },
                cancel: { label: 'Cancelar', className: 'btn-outline-secondary' },
            },
            callback: function (ok) {
                if (ok) {
                    aoConfirmar();
                }
            },
        });
    }

    $(document).on('submit', 'form[data-confirmar]', function (event) {
        var form = this;
        if ($(form).data('confirmado')) {
            return;
        }
        event.preventDefault();
        confirmar(form, function () {
            $(form).data('confirmado', true);
            form.submit();
        });
    });

    $(document).on('click', 'a[data-confirmar]', function (event) {
        var link = this;
        var token = $('input[name="csrfmiddlewaretoken"]').first().val();
        if (!token) {
            return;
        }
        event.preventDefault();
        confirmar(link, function () {
            var $form = $('<form method="post">')
                .attr('action', link.href)
                .append($('<input type="hidden" name="csrfmiddlewaretoken">').val(token))
                .appendTo('body');
            $form[0].submit();
        });
    });
});
