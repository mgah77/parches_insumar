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
        for vals in vals_list:
            if 'datas' in vals and vals['datas']:
                try:
                    # 1. Decodificar base64 a bytes
                    data_bytes = base64.b64decode(vals['datas'])
                    
                    # ---------------------------------------------------------
                    # Lógica del primer archivo (ir_attachment.py)
                    # Eliminar 'standalone="no"' si existe en el contenido
                    # ---------------------------------------------------------
                    if b'standalone="no"' in data_bytes:
                        data_bytes = data_bytes.replace(b' standalone="no"', b'')
                    
                    # ---------------------------------------------------------
                    # Lógica del segundo archivo (verisure.py)
                    # Verificar si es XML y transformar DTE -> EnvioDTE
                    # ---------------------------------------------------------
                    if b'<?xml' in data_bytes:
                        try:
                            # Decodificar bytes a string para parsear (ISO-8859-1 es estándar SII)
                            xml_str = data_bytes.decode('ISO-8859-1')
                            
                            # Intentar parsear XML
                            try:
                                root = ET.fromstring(xml_str)
                            except Exception:
                                # Si falla, intentar agregar el namespace manualmente
                                xml_str = xml_str.replace(
                                    '<DTE version="1.0">',
                                    '<DTE version="1.0" xmlns="http://www.sii.cl/SiiDte">'
                                )
                                root = ET.fromstring(xml_str)
                            
                            # Verificar si YA es EnvioDTE
                            if root.tag.endswith('}EnvioDTE') or root.tag == 'EnvioDTE':
                                pass  # Ya tiene estructura completa, mantener data_bytes actual
                            
                            # Si es DTE simple, transformarlo
                            elif root.tag.endswith('}DTE') or root.tag == 'DTE':
                                # Guardar copia del XML original
                                original_root = copy.deepcopy(root)
                                
                                # Extracción de datos con y sin namespace
                                namespace = '{http://www.sii.cl/SiiDte}'
                                
                                rut_emisor = original_root.find(f'.//{namespace}RUTEmisor') or original_root.find('.//RUTEmisor')
                                rut_receptor = original_root.find(f'.//{namespace}RUTRecep') or original_root.find('.//RUTRecep')
                                tipo_dte = original_root.find(f'.//{namespace}TipoDTE') or original_root.find('.//TipoDTE')
                                tmst_firma = original_root.find(f'.//{namespace}TmstFirma') or original_root.find('.//TmstFirma')
                                
                                # Crear estructura EnvioDTE
                                envio_dte = ET.Element('EnvioDTE')
                                envio_dte.set('version', '1.0')
                                envio_dte.set('xmlns', 'http://www.sii.cl/SiiDte')
                                envio_dte.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
                                envio_dte.set('xsi:schemaLocation', 'http://www.sii.cl/SiiDte EnvioDTE_v10.xsd')
                                
                                set_dte = ET.SubElement(envio_dte, 'SetDTE')
                                set_dte.set('ID', f"ID{uuid.uuid4().hex[:32]}")
                                
                                caratula = ET.SubElement(set_dte, 'Caratula')
                                caratula.set('version', '1.0')
                                
                                # Llenar Caratula
                                ET.SubElement(caratula, 'RutEmisor').text = rut_emisor.text if rut_emisor is not None else ''
                                ET.SubElement(caratula, 'RutEnvia').text = rut_emisor.text if rut_emisor is not None else ''
                                ET.SubElement(caratula, 'RutReceptor').text = rut_receptor.text if rut_receptor is not None else ''
                                ET.SubElement(caratula, 'FchResol').text = '2014-08-22'
                                ET.SubElement(caratula, 'NroResol').text = '80'
                                ET.SubElement(caratula, 'TmstFirmaEnv').text = tmst_firma.text if tmst_firma is not None else ''
                                
                                sub_tot = ET.SubElement(caratula, 'SubTotDTE')
                                ET.SubElement(sub_tot, 'TpoDTE').text = tipo_dte.text if tipo_dte is not None else '33'
                                ET.SubElement(sub_tot, 'NroDTE').text = '1'
                                
                                # Limpiar namespaces del root original para evitar duplicados
                                for elem in root.iter():
                                    if '}' in elem.tag:
                                        elem.tag = elem.tag.split('}', 1)[1]
                                
                                # Agregar el DTE al SetDTE
                                set_dte.append(root)
                                
                                # Buscar y copiar la firma
                                signature_in_dte = None
                                for elem in original_root.iter():
                                    if elem.tag.endswith('}Signature') or elem.tag == 'Signature':
                                        signature_in_dte = elem
                                        break
                                
                                if signature_in_dte is not None:
                                    signature_copy = copy.deepcopy(signature_in_dte)
                                    for elem in signature_copy.iter():
                                        if '}' in elem.tag:
                                            elem.tag = elem.tag.split('}', 1)[1]
                                    envio_dte.append(signature_copy)
                                
                                # Convertir el nuevo XML a bytes y sobrescribir data_bytes
                                xml_declaration = '<?xml version="1.0" encoding="ISO-8859-1"?>'
                                xml_content = xml_declaration + ET.tostring(envio_dte, encoding='unicode')
                                data_bytes = xml_content.encode('ISO-8859-1')
                                
                        except Exception:
                            # Si hay error en el parseo XML, continuar con data_bytes modificado (si aplica el paso anterior)
                            pass

                    # 2. Codificar de nuevo a base64 (ya sea limpiado o transformado)
                    vals['datas'] = base64.b64encode(data_bytes)
                    
                    # Si existe db_datas, actualizarlo también
                    if 'db_datas' in vals:
                        vals['db_datas'] = vals['datas']
                        
                except Exception:
                    # Si hay error general, continuar sin modificar
                    continue
        
        return super().create(vals_list)