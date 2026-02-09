# -*- coding: utf-8 -*-

import base64
import uuid
import xml.etree.ElementTree as ET
import copy
from odoo import api, models

class IrAttachmentInherit(models.Model):
    _inherit = 'ir.attachment'

    def _strip_namespace(self, elem):
        """
        Función auxiliar recursiva para eliminar los URIs de los namespaces
        de las etiquetas y atributos, evitando que ET.tostring genere prefijos ns0.
        """
        # Limpiar el tag (nombre de la etiqueta)
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]
        
        # Limpiar los atributos
        for key in list(elem.attrib.keys()):
            if '}' in key:
                new_key = key.split('}', 1)[1]
                elem.attrib[new_key] = elem.attrib.pop(key)
        
        # Recursión para los hijos
        for child in elem:
            self._strip_namespace(child)

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
                    
                    if b'<?xml' in data_bytes:
                        try:
                            xml_str = data_bytes.decode('ISO-8859-1')
                            
                            try:
                                root = ET.fromstring(xml_str)
                            except Exception:
                                xml_str = xml_str.replace(
                                    '<DTE version="1.0">',
                                    '<DTE version="1.0" xmlns="http://www.sii.cl/SiiDte">'
                                )
                                root = ET.fromstring(xml_str)
                            
                            if root.tag.endswith('}EnvioDTE') or root.tag == 'EnvioDTE':
                                pass
                            elif root.tag.endswith('}DTE') or root.tag == 'DTE':
                                original_root = copy.deepcopy(root)
                                namespace = '{http://www.sii.cl/SiiDte}'
                                
                                rut_emisor = original_root.find(f'.//{namespace}RUTEmisor') or original_root.find('.//RUTEmisor')
                                rut_receptor = original_root.find(f'.//{namespace}RUTRecep') or original_root.find('.//RUTRecep')
                                tipo_dte = original_root.find(f'.//{namespace}TipoDTE') or original_root.find('.//TipoDTE')
                                tmst_firma = original_root.find(f'.//{namespace}TmstFirma') or original_root.find('.//TmstFirma')
                                
                                envio_dte = ET.Element('EnvioDTE')
                                # IMPORTANTE: No definimos xmlns aquí para evitar ns0 en la creación
                                envio_dte.set('version', '1.0')
                                
                                set_dte = ET.SubElement(envio_dte, 'SetDTE')
                                set_dte.set('ID', f"ID{uuid.uuid4().hex[:32]}")
                                
                                caratula = ET.SubElement(set_dte, 'Caratula')
                                caratula.set('version', '1.0')
                                
                                ET.SubElement(caratula, 'RutEmisor').text = rut_emisor.text if rut_emisor is not None else ''
                                ET.SubElement(caratula, 'RutEnvia').text = rut_emisor.text if rut_emisor is not None else ''
                                ET.SubElement(caratula, 'RutReceptor').text = rut_receptor.text if rut_receptor is not None else ''
                                ET.SubElement(caratula, 'FchResol').text = '2014-08-22'
                                ET.SubElement(caratula, 'NroResol').text = '80'
                                ET.SubElement(caratula, 'TmstFirmaEnv').text = tmst_firma.text if tmst_firma is not None else ''
                                
                                sub_tot = ET.SubElement(caratula, 'SubTotDTE')
                                ET.SubElement(sub_tot, 'TpoDTE').text = tipo_dte.text if tipo_dte is not None else '33'
                                ET.SubElement(sub_tot, 'NroDTE').text = '1'
                                
                                dte_element = ET.SubElement(set_dte, 'DTE')
                                dte_element.set('version', '1.0')
                                
                                documento_element = None
                                if '}' in root.tag:
                                    doc_ns = root.tag.split('}')[0] + '}'
                                    documento_element = root.find(f'{doc_ns}Documento')
                                else:
                                    documento_element = root.find('Documento')
                                
                                if documento_element is not None:
                                    def copy_element_without_ns(source, target):
                                        for child in source:
                                            tag_name = child.tag
                                            if '}' in tag_name:
                                                tag_name = tag_name.split('}', 1)[1]
                                            
                                            new_element = ET.SubElement(target, tag_name)
                                            
                                            for attr_name, attr_value in child.attrib.items():
                                                if '}' in attr_name:
                                                    attr_name = attr_name.split('}', 1)[1]
                                                new_element.set(attr_name, attr_value)
                                            
                                            if child.text:
                                                new_element.text = child.text
                                            
                                            copy_element_without_ns(child, new_element)
                                    
                                    copy_element_without_ns(documento_element, dte_element)
                                
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
                                
                                xml_declaration = '<?xml version="1.0" encoding="ISO-8859-1"?>'
                                xml_content = xml_declaration + ET.tostring(envio_dte, encoding='unicode')
                                data_bytes = xml_content.encode('ISO-8859-1')
                                
                        except Exception as e:
                            import traceback
                            traceback.print_exc()
                            pass
                    
                    # ---------------------------------------------------------
                    # SEGUNDA TRANSFORMACIÓN: Del segundo archivo (FixDTE)
                    # 1. Corregir atributos del nodo DTE
                    # 2. Agregar segunda firma si es necesario
                    # 3. LIMPIEZA DE NAMESPACES (Solución al problema ns0:)
                    # ---------------------------------------------------------
                    if b'<?xml' in data_bytes:
                        try:
                            xml_str = data_bytes.decode('ISO-8859-1')
                            
                            try:
                                root = ET.fromstring(xml_str)
                            except:
                                try:
                                    xml_str_fixed = xml_str.replace(
                                        '<EnvioDTE',
                                        '<EnvioDTE xmlns="http://www.sii.cl/SiiDte"'
                                    )
                                    root = ET.fromstring(xml_str_fixed)
                                except:
                                    continue
                            
                            if root.tag.endswith('}EnvioDTE') or root.tag == 'EnvioDTE':
                                
                                # --- PASO 1: LIMPIEZA DE NAMESPACES ---
                                # Eliminar cualquier 'ns0' o URIs internas que generen prefijos
                                self._strip_namespace(root)
                                
                                # Re-asignar los atributos de namespace deseados manualmente
                                # Esto fuerza a que sea el namespace por defecto y no un prefijo
                                root.set('xmlns', 'http://www.sii.cl/SiiDte')
                                root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
                                
                                # Recorrer para buscar Signature y ponerle su xmlns específico
                                for sig in root.iter('Signature'):
                                    sig.set('xmlns', 'http://www.w3.org/2000/09/xmldsig#')

                                # --- PASO 2: Corrección de atributos y DTE ---
                                namespace = '{http://www.sii.cl/SiiDte}'
                                # Nota: Como limpiamos namespaces arriba, ahora buscamos sin URI o con lógica simple
                                
                                set_dte = root.find('.//SetDTE')
                                if set_dte is not None:
                                    dte_node = set_dte.find('DTE')
                                    if dte_node is not None:
                                        # Aseguramos atributos limpios
                                        dte_node.set('xmlns', 'http://www.sii.cl/SiiDte')
                                        if 'version' not in dte_node.attrib:
                                            dte_node.set('version', '1.0')
                                
                                # --- PASO 3: Duplicar firma ---
                                signature_original = None
                                for elem in root.iter():
                                    if elem.tag == 'Signature': # Ya está limpio
                                        signature_original = elem
                                        break
                                
                                if signature_original is not None:
                                    signature_count = 0
                                    for child in root:
                                        if child.tag == 'Signature':
                                            signature_count += 1
                                    
                                    if signature_count == 1:
                                        signature_copy = copy.deepcopy(signature_original)
                                        # La copia ya viene limpia si limpiamos el root antes,
                                        # pero aseguramos que no tenga basura
                                        root.append(signature_copy)
                                
                                # Convertir a string XML
                                xml_declaration = '<?xml version="1.0" encoding="ISO-8859-1"?>'
                                # Al no tener URIs en los tags internos, tostring no generará ns0:
                                xml_content = xml_declaration + ET.tostring(root, encoding='unicode')
                                data_bytes = xml_content.encode('ISO-8859-1')
                                
                        except Exception as e:
                            import traceback
                            traceback.print_exc()
                            continue
                    
                    vals['datas'] = base64.b64encode(data_bytes)
                    if 'db_datas' in vals:
                        vals['db_datas'] = vals['datas']
                        
                except Exception:
                    import traceback
                    traceback.print_exc()
                    continue
        
        return super().create(vals_list)