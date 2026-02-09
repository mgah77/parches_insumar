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
        Elimina los URIs de los namespaces de las etiquetas y atributos
        para evitar que ET.tostring genere prefijos ns0.
        """
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]
        
        for key in list(elem.attrib.keys()):
            if '}' in key:
                new_key = key.split('}', 1)[1]
                elem.attrib[new_key] = elem.attrib.pop(key)
        
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
                    # PRIMERA TRANSFORMACIÓN: Generar estructura EnvioDTE con 2 firmas
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
                                pass # Si ya es EnvioDTE, pasa a la segunda transformación
                            elif root.tag.endswith('}DTE') or root.tag == 'DTE':
                                original_root = copy.deepcopy(root)
                                namespace = '{http://www.sii.cl/SiiDte}'
                                
                                # Datos para la carátula
                                rut_emisor = original_root.find(f'.//{namespace}RUTEmisor') or original_root.find('.//RUTEmisor')
                                rut_receptor = original_root.find(f'.//{namespace}RUTRecep') or original_root.find('.//RUTRecep')
                                tipo_dte = original_root.find(f'.//{namespace}TipoDTE') or original_root.find('.//TipoDTE')
                                tmst_firma = original_root.find(f'.//{namespace}TmstFirma') or original_root.find('.//TmstFirma')
                                
                                # Crear estructura EnvioDTE
                                envio_dte = ET.Element('EnvioDTE')
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
                                
                                # Copiar Documento al DTE
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
                                
                                # --- MANEJO DE LAS FIRMAS (REQUISITO: 2 FIRMAS) ---
                                signature_in_dte = None
                                for elem in original_root.iter():
                                    if elem.tag.endswith('}Signature') or elem.tag == 'Signature':
                                        signature_in_dte = elem
                                        break
                                
                                if signature_in_dte is not None:
                                    # 1. Crear Firma para el DTE (Va dentro del nodo <DTE>)
                                    sig_dte = copy.deepcopy(signature_in_dte)
                                    for elem in sig_dte.iter():
                                        if '}' in elem.tag:
                                            elem.tag = elem.tag.split('}', 1)[1]
                                    # Insertar la firma dentro del elemento DTE
                                    dte_element.append(sig_dte)
                                    
                                    # 2. Crear Firma para el EnvioDTE (Va en el nodo raíz <EnvioDTE>)
                                    sig_envio = copy.deepcopy(signature_in_dte)
                                    for elem in sig_envio.iter():
                                        if '}' in elem.tag:
                                            elem.tag = elem.tag.split('}', 1)[1]
                                    # Insertar la firma al final del EnvioDTE
                                    envio_dte.append(sig_envio)
                                
                                xml_declaration = '<?xml version="1.0" encoding="ISO-8859-1"?>'
                                xml_content = xml_declaration + ET.tostring(envio_dte, encoding='unicode')
                                data_bytes = xml_content.encode('ISO-8859-1')
                                
                        except Exception as e:
                            import traceback
                            traceback.print_exc()
                            pass
                    
                    # ---------------------------------------------------------
                    # SEGUNDA TRANSFORMACIÓN: Limpieza y Aseguramiento de 2 Firmas
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
                                
                                # 1. Limpiar todos los namespaces (evitar ns0)
                                self._strip_namespace(root)
                                
                                # 2. Definir xmlns correctos en EnvioDTE (Raíz)
                                root.set('xmlns', 'http://www.sii.cl/SiiDte')
                                root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
                                
                                # 3. Definir xmlns correctos en el nodo DTE
                                dte_node = root.find('.//DTE')
                                if dte_node is not None:
                                    dte_node.set('xmlns', 'http://www.sii.cl/SiiDte')
                                    if 'version' not in dte_node.attrib:
                                        dte_node.set('version', '1.0')
                                
                                # 4. VERIFICAR Y COMPLETAR LAS FIRMAS
                                # Buscar firmas existentes
                                root_sigs = []
                                for child in root:
                                    if child.tag == 'Signature':
                                        root_sigs.append(child)
                                
                                dte_sigs = []
                                if dte_node is not None:
                                    for child in dte_node:
                                        if child.tag == 'Signature':
                                            dte_sigs.append(child)
                                
                                # Lógica: Asegurar que haya 1 en Raíz y 1 en DTE
                                # Si falta en Raíz, copiar la del DTE
                                if len(root_sigs) == 0 and len(dte_sigs) > 0:
                                    new_root_sig = copy.deepcopy(dte_sigs[0])
                                    root.append(new_root_sig)
                                    root_sigs.append(new_root_sig) # Actualizar lista
                                
                                # Si falta en DTE, copiar la de Raíz
                                elif len(dte_sigs) == 0 and len(root_sigs) > 0:
                                    new_dte_sig = copy.deepcopy(root_sigs[0])
                                    dte_node.append(new_dte_sig)
                                    dte_sigs.append(new_dte_sig)
                                
                                # 5. Asegurar que TODAS las firmas tengan el xmlns correcto
                                for sig in root.iter('Signature'):
                                    sig.set('xmlns', 'http://www.w3.org/2000/09/xmldsig#')
                                
                                xml_declaration = '<?xml version="1.0" encoding="ISO-8859-1"?>'
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