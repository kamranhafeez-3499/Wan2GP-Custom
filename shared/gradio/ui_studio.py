# Copyright (c) 2026 DeepBeepMeep - part of WanGP, WanGP Community License 2.0 (see LICENSE.txt)
"""WanGP's shared visual styling, preserving component and event definitions."""
import re
from pathlib import Path
from urllib.parse import quote

import gradio as gr

css_path = Path(__file__).with_name('ui_studio.css')
THEME_CHOICES = [('Blue Sky (Default)', 'default'), ('Classic Gradio', 'gradio'), ('Emerald', 'emerald'), ('Amethyst', 'amethyst'), ('Rose', 'rose'), ('Dark Clay', 'dark_clay')]
AZURE = gr.themes.colors.Color(name='azure', c50='#f1f7fc', c100='#d9ebfa', c200='#c2ddf5', c300='#91bce2', c400='#69a8df', c500='#357fc4', c600='#2b6ba8', c700='#205786', c800='#19466d', c900='#153956', c950='#10283e')
LILAC = gr.themes.colors.Color(name='lilac', c50='#f4f2ff', c100='#e9e6ff', c200='#d6d0ff', c300='#c4baff', c400='#b0a4ff', c500='#9b8cff', c600='#7f6cf5', c700='#6a57dc', c800='#5442b3', c900='#43358c', c950='#2a2160')
CLAY = gr.themes.colors.Color(name='clay', c50='#eceaf6', c100='#d6d4e6', c200='#b9b7cf', c300='#9a98b4', c400='#6f6d88', c500='#4a4a60', c600='#3a3b4e', c700='#323345', c800='#2c2d3c', c900='#22232f', c950='#1c1d27')
THEME_HUES = {'default': AZURE, 'emerald': 'emerald', 'amethyst': 'violet', 'rose': 'rose', 'dark_clay': LILAC}
DARK_THEMES = {'dark_clay'}

# Dark Clay: puffy surfaces (outer drop + inner light/shade) and pressed-in inputs.
CLAY_SHADOWS = {
    'puff': '8px 10px 22px rgba(0,0,0,.45), inset 4px 4px 8px rgba(255,255,255,.07), inset -4px -4px 8px rgba(0,0,0,.35)',
    'puff_small': '3px 4px 10px rgba(0,0,0,.4), inset 2px 2px 4px rgba(255,255,255,.07), inset -2px -2px 4px rgba(0,0,0,.35)',
    'dent': 'inset 3px 3px 7px rgba(0,0,0,.35), inset -3px -3px 7px rgba(255,255,255,.07)',
    'pressed': 'inset 3px 3px 6px rgba(0,0,0,.35), inset -2px -2px 5px rgba(255,255,255,.07)',
    'ring': '0 0 0 3px rgba(155,140,255,.45)',
    'float': '0 18px 40px rgba(0,0,0,.55), 0 4px 12px rgba(0,0,0,.35)',
}
CLAY_VALUES = {
    'body_background_fill': '#22232f', 'body_text_color': '#eceaf6', 'body_text_color_subdued': '#9a98b4',
    'background_fill_primary': '#2c2d3c', 'background_fill_secondary': '#22232f',
    'border_color_primary': '#3a3b4e', 'border_color_accent': '#9b8cff',
    'block_background_fill': '#2c2d3c', 'block_border_color': 'transparent', 'block_border_width': '0px',
    'block_shadow': 'none', 'block_label_text_color': '#c4baff', 'block_title_text_color': '#c4baff',
    'block_label_background_fill': 'transparent', 'block_title_background_fill': 'transparent',
    'input_background_fill': '#1c1d27', 'input_background_fill_focus': '#1c1d27', 'input_border_color': 'transparent',
    'input_border_color_focus': 'transparent', 'input_shadow': CLAY_SHADOWS['dent'],
    'input_shadow_focus': CLAY_SHADOWS['dent'] + ', ' + CLAY_SHADOWS['ring'], 'input_placeholder_color': '#6f6d88',
    'button_primary_background_fill': 'linear-gradient(135deg, #b8adff, #9b8cff 50%, #7f6cf5)',
    'button_primary_background_fill_hover': 'linear-gradient(135deg, #c4baff, #a99cff 50%, #8b7af7)',
    'button_primary_text_color': '#16151f', 'button_primary_border_color': 'transparent',
    'button_primary_shadow': '0 8px 20px rgba(155,140,255,.32), inset 3px 3px 6px rgba(255,255,255,.4), inset -3px -4px 8px rgba(0,0,0,.2)',
    'button_primary_shadow_hover': '0 10px 24px rgba(155,140,255,.4), inset 3px 3px 6px rgba(255,255,255,.4), inset -3px -4px 8px rgba(0,0,0,.2)',
    'button_primary_shadow_active': 'inset 3px 4px 8px rgba(0,0,0,.3), inset -2px -2px 4px rgba(255,255,255,.25)',
    'button_secondary_background_fill': '#323345', 'button_secondary_background_fill_hover': '#38394d',
    'button_secondary_text_color': '#eceaf6', 'button_secondary_border_color': 'transparent',
    'button_secondary_shadow': CLAY_SHADOWS['puff_small'], 'button_secondary_shadow_active': CLAY_SHADOWS['pressed'],
    'button_cancel_background_fill': '#323345', 'button_cancel_text_color': '#ff8a9a',
    'slider_color': '#9b8cff', 'checkbox_background_color': '#1c1d27', 'checkbox_background_color_selected': '#9b8cff',
    'checkbox_border_color': '#3a3b4e', 'checkbox_border_color_selected': '#9b8cff',
    'checkbox_label_background_fill': '#323345', 'checkbox_label_background_fill_selected': '#3d3a5e',
    'checkbox_label_text_color_selected': '#eceaf6', 'color_accent': '#9b8cff', 'color_accent_soft': '#3d3a5e',
    'panel_background_fill': '#2c2d3c', 'panel_border_color': 'transparent',
    'shadow_drop': CLAY_SHADOWS['puff_small'], 'shadow_drop_lg': CLAY_SHADOWS['float'],
    'table_even_background_fill': '#2c2d3c', 'table_odd_background_fill': '#272836',
    'link_text_color': '#c4baff', 'link_text_color_hover': '#e9e6ff', 'loader_color': '#9b8cff',
    'stat_background_fill': '#3d3a5e', 'error_background_fill': '#3a2530', 'error_text_color': '#ff8a9a', 'error_border_color': '#7a3c4a',
    'accordion_text_color': '#c4baff', 'code_background_fill': '#1c1d27',
}


def create_dark_clay_theme(**sizes):
    sizes['radius_size'] = gr.themes.Size('4px', '6px', '10px', '14px', '18px', '22px', '28px', name='clay_radius')
    theme = gr.themes.Soft(font=[gr.themes.GoogleFont('Nunito'), gr.themes.Font('Segoe UI'), gr.themes.Font('system-ui'), gr.themes.Font('sans-serif')], primary_hue=LILAC, secondary_hue=LILAC, neutral_hue=CLAY, **sizes)
    # Same values in light and dark mode: the theme always renders dark.
    theme.set(**CLAY_VALUES, **{f'{key}_dark': value for key, value in CLAY_VALUES.items() if hasattr(theme, f'{key}_dark')})
    theme.name = 'dark_clay'
    return theme


def get_theme_javascript(name):
    if name not in DARK_THEMES:
        return ""
    return "\n(function () { document.body.classList.add('dark'); document.documentElement.style.colorScheme = 'dark'; })();\n"


def create_theme(name, **sizes):
    if name == 'gradio':
        return None
    if name == 'dark_clay':
        return create_dark_clay_theme(**sizes)
    theme = gr.themes.Soft(font=['Verdana'], primary_hue=THEME_HUES[name], secondary_hue=AZURE if name == 'default' else 'indigo', neutral_hue='slate', **sizes)
    if name == 'default':
        theme.set(background_fill_primary='*neutral_50', slider_color_dark='*primary_400', checkbox_label_background_fill_selected='*primary_600')
    if name != 'default':
        theme.name = name
    return theme


icons = {
    'Apply': '<path d="m5 12 4 4L19 6"/>',
    'Refresh': '<path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-1l2 6M4 12l2 6a7 7 0 0 0 12-1"/>',
    'Save': '<path d="M5 3h12l4 4v14H3V3h2Zm2 0v7h10V3M7 21v-7h10v7"/>',
    'Delete': '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
    'Generate': '<path d="m8 4 12 8-12 8Z"/>',
    'Set Settings as Default': '<path d="m5 12 4 4L19 6"/>',
    'Export Settings to File': '<path d="M10 3H4v18h15v-7M14 3h7v7M11 13 21 3"/>',
    'Reset Settings': '<path d="M4 8a9 9 0 1 1-1 7M4 3v5h5M9 11h7M9 16h7M11 9v4M14 14v4"/>',
    'Enhance Prompt': '<path d="m15 4 1.8 5.2L22 11l-5.2 1.8L15 18l-1.8-5.2L8 11l5.2-1.8ZM5 2v6M2 5h6M5 16v6M2 19h6"/>',
    'Go Ahead Save it !': '<path d="m5 12 4 4L19 6"/>',
    'Go Ahead Delete it !': '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
    "Don't do it !": '<path d="m6 6 12 12M6 18 18 6"/>',
    'Download': '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
    'Exit': '<path d="M9 4H4v16h5M8 12h13m-5-5 5 5-5 5"/>',
    'Abort': '<rect x="5" y="5" width="14" height="14" rx="2"/>',
    'One More': '<rect x="3" y="3" width="12" height="14" rx="2"/><path d="M7 21h10a2 2 0 0 0 2-2v-4M9 7v6M6 10h6"/>',
    'Extend': '<path d="M4 5v14M4 12h16m-5-5 5 5-5 5"/>',
    'Pause': '<rect x="5" y="4" width="4" height="16" rx="1"/><rect x="15" y="4" width="4" height="16" rx="1"/>',
    'Resume': '<path d="m8 4 12 8-12 8Z"/>',
    'Early Stop': '<path d="m4 5 10 7-10 7Z"/><path d="M19 5v14"/>',
    'Add New Prompt To Queue': '<path d="M4 5h11M4 10h11M4 15h6M17 13v8m-4-4h8"/>',
}
icon_css = []
for index, (label, paths) in enumerate(icons.items()):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{paths}</svg>'
    icon_css.append(f'.wangp-studio-icon-{index} {{ --studio-icon: url("data:image/svg+xml,{quote(svg)}"); }}')


def style_config(config, theme):
    components = {component['id']: component for component in config['components']}
    paths = {}
    def visit(node, parents=()):
        paths[node['id']] = (*parents, node['id'])
        for child in node.get('children', []):
            visit(child, paths[node['id']])
    visit(config['layout'])
    scope = config['layout']['id']
    navigation = {next(node for node in reversed(paths[c['id']]) if components[node]['type'] == 'row') for c in components.values() if c['props'].get('elem_id') == 'family_list'}
    kinds = {kind: 'field' for kind in ('textbox', 'dropdown', 'slider', 'number', 'checkbox', 'checkboxgroup', 'radio', 'hierarchyselector', 'rangeslider', 'file', 'image', 'audio')}
    kinds.update(button='button', uploadbutton='button', downloadbutton='button', accordion='accordion', tabs='tabs', gallery='gallery', video='gallery')
    selectors = {'wangp-studio-scope': [f'#component-{scope}'], 'wangp-studio-dropdown': []}
    for component_id, component in components.items():
        if component_id not in paths or scope not in paths[component_id]:
            continue
        if component['type'] == 'dropdown':
            selectors['wangp-studio-dropdown'].append('#' + (component['props'].get('elem_id') or f'component-{component_id}'))
        if navigation.intersection(paths[component_id]):
            continue
        extra = []
        if component['type'] in kinds:
            extra.append('wangp-studio-' + kinds[component['type']])
        if component['type'] == 'button':
            # Models can rename the prompt enhancer (Write, Magic Prompt, etc.).
            label = 'Enhance Prompt' if 'btn_centered' in (component['props'].get('elem_classes') or []) else component['props']['value']
            if label in icons:
                extra.extend(['wangp-studio-icon', f'wangp-studio-icon-{list(icons).index(label)}'])
            if label in ('Generate', 'Add New Prompt To Queue'):
                extra.append('wangp-studio-generation-action')
            if label == 'Enhance Prompt':
                extra.append('wangp-studio-enhancer')
        if extra:
            element_id = component['props'].get('elem_id') or f'component-{component_id}'
            for name in extra:
                selectors.setdefault(name, []).append(f'#{element_id}')
    scope_selector = selectors['wangp-studio-scope'][0]
    def selector(match):
        name = match.group()[1:]
        targets = selectors[name]
        if name == 'wangp-studio-scope':
            return scope_selector
        return f':where({scope_selector}) :is({",".join(targets)})'
    # Stable component IDs survive explicit elem_classes updates during swaps.
    # No component metadata, constructors, events or client observers are changed.
    css = css_path.read_text(encoding='utf8')
    if isinstance(theme, gr.themes.Default):
        css += '\n' + css_path.with_name('ui_studio_classic.css').read_text(encoding='utf8')
    elif theme.name in ('emerald', 'amethyst', 'rose', 'dark_clay'):
        css += '\n' + css_path.with_name(f'ui_studio_{theme.name}.css').read_text(encoding='utf8')
    css += '\n' + '\n'.join(icon_css)
    config['css'] = (config['css'] or '') + '\n' + re.sub(r'\.wangp-studio-[a-z0-9-]+', selector, css)
    return config


class Blocks(gr.Blocks):
    def get_config_file(self):
        return style_config(super().get_config_file(), self.theme)
