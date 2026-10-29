/*
 * Tela do assistente: envia a pergunta por AJAX ($.ajax) com o token CSRF
 * e mostra a resposta, que já chega sanitizada pelo servidor (nh3).
 * Sem JavaScript, o formulário é enviado normalmente.
 */
$(function () {
    var $form = $('#form-pergunta');
    if (!$form.length) {
        return;
    }
    var $campo = $('#id_pergunta');
    var $botao = $form.find('button[type="submit"]');
    var $contador = $('#contador-pergunta');
    var $conversa = $('#conversa');
    var maximo = parseInt($campo.attr('maxlength'), 10);

    function rolarParaOFim() {
        $conversa.scrollTop($conversa[0].scrollHeight);
    }

    function atualizarContador() {
        $contador.text($campo.val().length + '/' + maximo);
    }

    // Texto do usuário entra sempre com .text(); só a resposta do servidor entra como HTML.
    function adicionar(papel, conteudo, classeExtra, ehHtml) {
        var $mensagem = $('<div>').addClass('assistente-msg assistente-msg-' + papel);
        if (classeExtra) {
            $mensagem.addClass(classeExtra);
        }
        if (ehHtml) {
            $mensagem.html(conteudo);
        } else {
            $mensagem.append($('<p>').text(conteudo));
        }
        $conversa.find('.assistente-vazio').remove();
        $conversa.append($mensagem);
        rolarParaOFim();
        return $mensagem;
    }

    function ocupado(sim) {
        $botao.prop('disabled', sim).text(sim ? 'Pensando…' : 'Enviar');
        $campo.prop('readonly', sim);
    }

    $campo.on('input', atualizarContador);

    $campo.on('keydown', function (event) {
        if (event.key === 'Enter' && !event.shiftKey && !event.originalEvent.isComposing) {
            event.preventDefault();
            $form.trigger('submit');
        }
    });

    $form.on('submit', function (event) {
        event.preventDefault();
        var pergunta = $.trim($campo.val());
        if (!pergunta || $botao.prop('disabled')) {
            return;
        }

        var $pergunta = adicionar('user', pergunta);
        var $pensando = adicionar('model', 'Pensando…', 'assistente-pensando');
        $campo.val('');
        atualizarContador();
        ocupado(true);

        $.ajax({
            url: $form.attr('action'),
            method: 'POST',
            data: { pergunta: pergunta },
            dataType: 'json',
            headers: { 'X-CSRFToken': $form.find('input[name="csrfmiddlewaretoken"]').val() },
        })
            .done(function (dados) {
                if (dados.ok) {
                    adicionar('model', dados.resposta_html, null, true);
                } else {
                    adicionar('model', dados.erro, 'assistente-' + dados.tipo);
                }
            })
            .fail(function (xhr) {
                var dados = xhr.responseJSON || {};
                // A pergunta não foi guardada: devolve o texto ao campo para tentar de novo.
                $pergunta.remove();
                $campo.val(pergunta);
                atualizarContador();
                adicionar('model', dados.erro || 'Não foi possível falar com o assistente. Tente de novo.', 'assistente-erro');
            })
            .always(function () {
                $pensando.remove();
                ocupado(false);
                $campo.trigger('focus');
            });
    });

    atualizarContador();
    rolarParaOFim();
});
