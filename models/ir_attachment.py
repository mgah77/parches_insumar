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
                    # PRIMERA TRANSFORMACIÓN: Del primer archivo (ir_attachment.py)
                    # 1. Eliminar 'standalone="no"' si existe
                    # 2. Transformar DTE simple -> EnvioDTE
                    # ---------------------------------------------------------
                    if b'standalone="no"' in data_bytes:
                        data_bytes = data_bytes.replace(b' standalone="no"', b'')
                    
                    # Si es XML, procesar transformación
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
                                # Ya tiene estructura completa, mantener como está
                                pass
                            
                            # Si es DTE simple, transformarlo a EnvioDTE
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
                                
                                # Crear un nuevo elemento DTE con namespace SII en lugar de copiar el original
                                dte_element = ET.SubElement(set_dte, 'DTE')
                                dte_element.set('version', '1.0')
                                
                                # IMPORTANTE: Eliminar completamente namespaces como ns0: y reemplazar por elementos sin namespace
                                # Buscar el elemento Documento dentro del root original
                                documento_element = None
                                
                                # Buscar el Documento con o sin namespace
                                if '}' in root.tag:
                                    # Si el root tiene namespace, buscar Documento con namespace
                                    doc_ns = root.tag.split('}')[0] + '}'
                                    documento_element = root.find(f'{doc_ns}Documento')
                                else:
                                    # Si el root no tiene namespace, buscar Documento sin namespace
                                    documento_element = root.find('Documento')
                                
                                if documento_element is not None:
                                    # Función recursiva para copiar elementos sin namespace
                                    def copy_element_without_ns(source, target):
                                        for child in source:
                                            # Obtener el nombre del tag sin namespace
                                            tag_name = child.tag
                                            if '}' in tag_name:
                                                tag_name = tag_name.split('}', 1)[1]
                                            
                                            # Crear nuevo elemento sin namespace
                                            new_element = ET.SubElement(target, tag_name)
                                            
                                            # Copiar atributos
                                            for attr_name, attr_value in child.attrib.items():
                                                # Limpiar namespace de atributos también si es necesario
                                                if '}' in attr_name:
                                                    attr_name = attr_name.split('}', 1)[1]
                                                new_element.set(attr_name, attr_value)
                                            
                                            # Copiar texto
                                            if child.text:
                                                new_element.text = child.text
                                            
                                            # Copiar hijos recursivamente
                                            copy_element_without_ns(child, new_element)
                                    
                                    # Copiar Documento y sus hijos sin namespaces
                                    copy_element_without_ns(documento_element, dte_element)
                                
                                # Buscar y copiar la firma del DTE original
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
                                
                                # Convertir el nuevo XML a bytes
                                xml_declaration = '<?xml version="1.0" encoding="ISO-8859-1"?>'
                                xml_content = xml_declaration + ET.tostring(envio_dte, encoding='unicode')
                                data_bytes = xml_content.encode('ISO-8859-1')
                                
                        except Exception as e:
                            # Si hay error en el parseo XML, continuar con data_bytes modificado
                            import traceback
                            traceback.print_exc()
                            pass
                    
                    # ---------------------------------------------------------
                    # SEGUNDA TRANSFORMACIÓN: Del segundo archivo (FixDTE)
                    # 1. Corregir atributos del nodo DTE
                    # 2. Agregar segunda firma si es necesario
                    # ---------------------------------------------------------
                    # Verificar si el contenido actual es XML
                    if b'<?xml' in data_bytes:
                        try:
                            xml_str = data_bytes.decode('ISO-8859-1')
                            
                            # Parsear XML
                            try:
                                root = ET.fromstring(xml_str)
                            except:
                                # Si falla el parseo, intentar inyectar namespace
                                try:
                                    xml_str_fixed = xml_str.replace(
                                        '<EnvioDTE',
                                        '<EnvioDTE xmlns="http://www.sii.cl/SiiDte"'
                                    )
                                    root = ET.fromstring(xml_str_fixed)
                                except:
                                    # Si falla todo, continuar sin modificar
                                    continue
                            
                            # Verificar si es un EnvioDTE (después de la primera transformación o ya lo era)
                            if root.tag.endswith('}EnvioDTE') or root.tag == 'EnvioDTE':
                                
                                # --- PASO 1: Asegurar que todos los elementos tengan el namespace correcto ---
                                # Verificar y corregir el DTE dentro de SetDTE
                                namespace = '{http://www.sii.cl/SiiDte}'
                                
                                # Buscar el SetDTE
                                set_dte = root.find(f'.//{namespace}SetDTE')
                                if set_dte is None:
                                    set_dte = root.find('.//SetDTE')
                                
                                if set_dte is not None:
                                    # Buscar el DTE dentro de SetDTE
                                    dte_node = set_dte.find(f'{namespace}DTE')
                                    if dte_node is None:
                                        dte_node = set_dte.find('DTE')
                                    
                                    # Si encontramos el DTE, asegurar que tenga los atributos correctos
                                    if dte_node is not None:
                                        dte_node.set('xmlns', 'http://www.sii.cl/SiiDte')
                                        if 'version' not in dte_node.attrib:
                                            dte_node.set('version', '1.0')
                                        
                                        # Buscar y eliminar cualquier atributo de namespace incorrecto como ns0:
                                        for elem in dte_node.iter():
                                            # Eliminar atributos con namespace incorrecto
                                            attrs_to_remove = []
                                            for attr_name in elem.attrib:
                                                if attr_name.startswith('{') and '}' in attr_name:
                                                    attrs_to_remove.append(attr_name)
                                            for attr in attrs_to_remove:
                                                del elem.attrib[attr]
                                
                                # --- PASO 2: Agregar la falta de la segunda firma ---
                                # Buscar la firma existente (generalmente dentro de Documento/DTE)
                                signature_original = None
                                for elem in root.iter():
                                    if elem.tag.endswith('}Signature') or elem.tag == 'Signature':
                                        signature_original = elem
                                        break
                                
                                if signature_original is not None:
                                    # Contar cuántas firmas ya existen en el nivel raíz (EnvioDTE)
                                    signature_count = 0
                                    for child in root:
                                        if child.tag.endswith('}Signature') or child.tag == 'Signature':
                                            signature_count += 1
                                    
                                    # Si solo hay una firma en el nivel raíz, agregar una copia
                                    if signature_count == 1:
                                        # Crear una copia profunda de la firma
                                        signature_copy = copy.deepcopy(signature_original)
                                        
                                        # Limpiar namespaces de la copia
                                        for elem in signature_copy.iter():
                                            if '}' in elem.tag:
                                                elem.tag = elem.tag.split('}', 1)[1]
                                        
                                        # Adjuntar la copia al final del EnvioDTE
                                        root.append(signature_copy)
                                
                                # Convertir a string XML
                                xml_declaration = '<?xml version="1.0" encoding="ISO-8859-1"?>'
                                xml_content = xml_declaration + ET.tostring(root, encoding='unicode')
                                data_bytes = xml_content.encode('ISO-8859-1')
                                
                        except Exception as e:
                            # Si hay error, continuar sin modificar
                            import traceback
                            traceback.print_exc()
                            continue
                    
                    # 3. Codificar de nuevo a base64 (después de ambas transformaciones)
                    vals['datas'] = base64.b64encode(data_bytes)
                    
                    # Si existe db_datas, actualizarlo también
                    if 'db_datas' in vals:
                        vals['db_datas'] = vals['datas']
                        
                except Exception:
                    # Si hay error general, continuar sin modificar
                    import traceback
                    traceback.print_exc()
                    continue
        
        return super().create(vals_list)