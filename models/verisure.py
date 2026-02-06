# -*- coding: utf-8 -*-

import base64
import uuid
import xml.etree.ElementTree as ET
import copy
from odoo import api, models

class IrAttachmentInherit(models.Model):
    _inherit = 'ir.attachment'

    @api.model_create_multi
    def create(self, vals_list):
        namespace_sii = 'http://www.sii.cl/SiiDte'

        for vals in vals_list:
            if 'datas' in vals and vals['datas']:
                try:
                    # Decodificar base64
                    xml_bytes = base64.b64decode(vals['datas'])
                    
                    # Verificar si es XML
                    if b'<?xml' in xml_bytes:
                        xml_str = xml_bytes.decode('ISO-8859-1')
                        
                        # Parsear XML
                        try:
                            root = ET.fromstring(xml_str)
                        except:
                            # Intento de recuperación simple agregando namespace por si acaso
                            xml_str = xml_str.replace('<DTE version="1.0">', '<DTE version="1.0" xmlns="http://www.sii.cl/SiiDte">')
                            root = ET.fromstring(xml_str)

                        clean_tag = root.tag.split('}')[-1]

                        # --- CASO 1: Llega un DTE Suelto (Hay que envolverlo) ---
                        if clean_tag == 'DTE':
                            # Guardar copia para extraer firma
                            original_root = copy.deepcopy(root)
                            
                            # Buscar datos para la carátula
                            rut_emisor = original_root.find('.//RUTEmisor') or original_root.find(f'.//{namespace_sii}RUTEmisor')
                            rut_receptor = original_root.find('.//RUTRecep') or original_root.find(f'.//{namespace_sii}RUTRecep')
                            tipo_dte = original_root.find('.//TipoDTE') or original_root.find(f'.//{namespace_sii}TipoDTE')
                            tmst_firma = original_root.find('.//TmstFirma') or original_root.find(f'.//{namespace_sii}TmstFirma')
                            
                            # Crear estructura EnvioDTE
                            envio_dte = ET.Element('EnvioDTE')
                            envio_dte.set('version', '1.0')
                            envio_dte.set('xmlns', namespace_sii)
                            envio_dte.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
                            envio_dte.set('xsi:schemaLocation', 'http://www.sii.cl/SiiDte EnvioDTE_v10.xsd')
                            
                            set_dte = ET.SubElement(envio_dte, 'SetDTE')
                            set_dte.set('ID', f"ID{uuid.uuid4().hex[:32]}")
                            
                            caratula = ET.SubElement(set_dte, 'Caratula')
                            caratula.set('version', '1.0')
                            
                            # Llenar Carátula
                            ET.SubElement(caratula, 'RutEmisor').text = rut_emisor.text if rut_emisor is not None else ''
                            ET.SubElement(caratula, 'RutEnvia').text = rut_emisor.text if rut_emisor is not None else ''
                            ET.SubElement(caratula, 'RutReceptor').text = rut_receptor.text if rut_receptor is not None else ''
                            ET.SubElement(caratula, 'FchResol').text = '2014-08-22'
                            ET.SubElement(caratula, 'NroResol').text = '80'
                            ET.SubElement(caratula, 'TmstFirmaEnv').text = tmst_firma.text if tmst_firma is not None else ''
                            
                            sub_tot = ET.SubElement(caratula, 'SubTotDTE')
                            ET.SubElement(sub_tot, 'TpoDTE').text = tipo_dte.text if tipo_dte is not None else '33'
                            ET.SubElement(sub_tot, 'NroDTE').text = '1'
                            
                            # Preparar el DTE para agregarlo
                            # Limpiamos tags y FORZAMOS el xmlns en el nodo DTE para evitar el problema del Caso 2
                            for elem in root.iter():
                                if '}' in elem.tag:
                                    elem.tag = elem.tag.split('}', 1)[1]
                            
                            root.set('xmlns', namespace_sii) # Corrección preventiva
                            set_dte.append(root)
                            
                            # Mover firma al final del EnvioDTE (Copia)
                            signature_node = None
                            for elem in original_root.iter():
                                if elem.tag.endswith('}Signature') or elem.tag == 'Signature':
                                    signature_node = elem
                                    break
                            
                            if signature_node is not None:
                                sig_copy = copy.deepcopy(signature_node)
                                for elem in sig_copy.iter():
                                    if '}' in elem.tag:
                                        elem.tag = elem.tag.split('}', 1)[1]
                                envio_dte.append(sig_copy)
                            
                            # Actualizar root para guardar
                            root = envio_dte

                        # --- CASO 2: Llega un EnvioDTE (Hay que corregir atributos y firma externa) ---
                        elif clean_tag == 'EnvioDTE':
                            # 1. Corregir atributo xmlns en el DTE interno
                            dte_node = root.find('.//DTE')
                            if dte_node is not None:
                                if dte_node.get('xmlns') != namespace_sii:
                                    dte_node.set('xmlns', namespace_sii)
                            
                            # 2. Agregar segunda firma si no existe afuera
                            # Buscamos si ya hay una firma directa en EnvioDTE (no dentro de DTE)
                            has_external_signature = False
                            for child in root:
                                if child.tag == 'Signature' or child.tag.endswith('}Signature'):
                                    has_external_signature = True
                                    break
                            
                            if not has_external_signature:
                                # Buscamos firma interna para copiarla
                                internal_signature = None
                                for elem in root.iter():
                                    if elem.tag.endswith('}Signature') or elem.tag == 'Signature':
                                        internal_signature = elem
                                        break # Tomamos la primera que encontramos
                                
                                if internal_signature is not None:
                                    sig_copy = copy.deepcopy(internal_signature)
                                    for elem in sig_copy.iter():
                                        if '}' in elem.tag:
                                            elem.tag = elem.tag.split('}', 1)[1]
                                    root.append(sig_copy)

                        # Finalmente guardamos los cambios (aplica a ambos casos)
                        xml_declaration = '<?xml version="1.0" encoding="ISO-8859-1"?>'
                        xml_content = xml_declaration + ET.tostring(root, encoding='unicode')
                        vals['datas'] = base64.b64encode(xml_content.encode('ISO-8859-1'))
                        
                        if 'db_datas' in vals:
                            vals['db_datas'] = vals['datas']

                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    continue
        
        return super().create(vals_list)